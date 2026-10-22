"""S1 reference-model runner; smoke outputs cannot authorize benchmark claims."""
from dataclasses import asdict
from pathlib import Path
import json
import platform
import subprocess
import time
import importlib.metadata
import numpy as np
import pandas as pd
import optuna
import yaml
from threadpoolctl import threadpool_limits
from outage.data import load_outage_dataset, RAW, ANALYSIS, WEATHER, WEATHER_UNITS
from .config import Config, load_config, CONFIG_PATH
from .targets import labels, targets
from .features import features
from .splits import monthly_folds, TestIndexGuard
from .models import logistic, baseline
from .metrics import brier, bss, classification, reliability
from .artifacts import cache_key, write_predictions, select, threshold, read_predictions
from .inference import block_length, bootstrap, descriptive_ranks

ROOT = Path(__file__).resolve().parents[2]

def fit_predict(model, X: pd.DataFrame, y: pd.Series, train: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    """Fit any fit/predict_proba estimator, retaining only observed targets."""
    use = train[y.iloc[train].notna().to_numpy()]
    model.fit(X.iloc[use],y.iloc[use].to_numpy())
    probabilities = np.asarray(model.predict_proba(X.iloc[prediction]))
    return probabilities[:,1] if probabilities.ndim == 2 else probabilities

def label_disagreement(frame: pd.DataFrame, output: Path) -> pd.DataFrame:
    """Write timestamped label disagreements directly from source energies."""
    table = frame[['grid_kwh','generator_kwh']].copy()
    table['primary'] = labels(frame,'grid_zero'); table['s_gen'] = labels(frame,'generator_positive')
    table = table[table.primary != table.s_gen]
    output.parent.mkdir(parents=True,exist_ok=True); table.to_csv(output,index_label='timestamp')
    return table

def run(output: Path | None = None, smoke: bool = True, config: Config | None = None, kind: str = 'a', setting: str = 'W0') -> pd.DataFrame:
    """Run BG folds x horizons x evaluation seeds, with saved validation selection."""
    c = config or load_config(); output = Path(output or ROOT/('results/S1/wp2_smoke' if smoke else 'results/S1'))
    if kind not in ('a','b'): raise ValueError('Duration estimators arrive in WP3; use targets(c) for censored outcomes')
    calendar_path = ROOT/c.calendar_path
    if not smoke:
        if not calendar_path.exists(): raise RuntimeError('Approved calendar missing; benchmark blocked')
        evidence = ROOT/c.hour_evidence_path
        caps_path = ROOT/c.timing_caps_path
        if not evidence.exists() or not json.loads(evidence.read_text()).get('verified', False):
            raise RuntimeError('Independent hour-convention clearance missing; benchmark blocked')
        if not caps_path.exists(): raise RuntimeError('Timing-cap addendum missing; benchmark blocked')
        frozen = output/'PROTOCOL.sha256'
        required = [ROOT/'method/S1_protocol.md', CONFIG_PATH, calendar_path, caps_path]
        import hashlib
        if not frozen.exists() or any(hashlib.sha256(p.read_bytes()).hexdigest() not in frozen.read_text() for p in required):
            raise RuntimeError('Protocol/config/calendar/timing hashes missing or stale')
    for directory in ['config','predictions/innerval','metrics','inference','figures','tests','leakage_randomsplit','dispatch']:
        (output/directory).mkdir(parents=True,exist_ok=True)
    data = load_outage_dataset(); y = labels(data,c.label)
    disagreements = label_disagreement(data,ROOT/'results/S1/label_disagreement.csv')
    code = sorted((ROOT/'src/eval').glob('*.py'))
    effective = output/'config/effective.yaml'
    effective.write_text(yaml.safe_dump(asdict(c),sort_keys=True))
    paths = [CONFIG_PATH,effective,*code,RAW/ANALYSIS,RAW/WEATHER]
    if calendar_path.exists(): paths.append(calendar_path)
    key = cache_key(paths)
    (output/'config/S1_frozen.yaml').write_bytes(CONFIG_PATH.read_bytes())
    (output/'config/run.json').write_text(json.dumps({'smoke':smoke,'cache_key':key,'label':c.label,'target':kind,'weather':setting,'trial_budget':c.smoke_trials if smoke else c.trials,'bootstrap_B':c.smoke_B if smoke else c.bootstrap_B,'calendar_present':calendar_path.exists(),'hour_convention_verified':not smoke},indent=2))
    (output/'config/environment.json').write_text(json.dumps({'python':platform.python_version(),**{name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn','optuna','pyarrow','PyYAML']}},indent=2))
    (output/'config/git_commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    if smoke: (output/'PROTOCOL.sha256').write_text(cache_key([ROOT/'method/S1_protocol.md'])+' protocol (smoke snapshot, NOT freeze)\n'+key+' config/code/data\n')
    deviations = ['Harness smoke only; not the benchmark. Consumption-derived labels, not independently verified availability.', 'Hour-beginning convention is a protocol assumption, not established by workbook documentation; leakage gate remains unresolved.', 'Approved calendar unavailable: holiday/Ramadan features omitted in smoke only.', 'Smoke uses the full logistic trial budget. No Q1/G1 conclusions: later model families are absent.', 'No benchmark timing-cap addendum or approved protocol freeze is claimed.', 'Implemented strongest-baseline pool is incomplete: later work packages add remaining baselines.', 'PR-AUC uses non-interpolated average precision; threshold ties choose the smallest candidate. Markov sparse-cell fallback applies to the whole conditioning row.', 'BCa uses delete-nonoverlapping-block acceleration within month; requires lead acceptance.']
    (output/'DEVIATIONS.md').write_text('\n'.join('- '+x for x in deviations))
    pd.DataFrame([{'rows':len(data),'missing_labels':int(y.isna().sum()),'disagreement_hours':len(disagreements)}]).to_csv(output/'data_audit.csv',index=False)
    calendar = None
    if calendar_path.exists():
        calendar = pd.read_csv(calendar_path,comment='#',parse_dates=['date']).set_index('date')
        calendar.index = calendar.index.tz_localize(y.index.tz)
    metrics_rows = []; selection_rows = []; tuning_rows = []; timing_rows = []; all_test = {}; all_ref = {}; all_strong = {}
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    for h in (c.horizons if kind == 'a' else c.horizons_b):
        X = features(y,data[list(WEATHER_UNITS)],setting,h,calendar,c); target = targets(y,kind,h)['value']; params = None
        for fold in monthly_folds(y.index,h,c):
            print(f'h={h} fold={fold.number}',flush=True)
            guard = TestIndexGuard(fold.test)
            val = fold.inner_val[target.iloc[fold.inner_val].notna().to_numpy()]
            if fold.number in c.retune_folds:
                sampler = optuna.samplers.TPESampler(seed=c.sampler_seed,n_startup_trials=c.startup_trials,multivariate=True)
                study = optuna.create_study(direction='minimize',sampler=sampler)
                def objective(trial):
                    start = time.perf_counter()
                    p = {'C':trial.suggest_float('C',*c.logistic_C,log=True),'penalty':trial.suggest_categorical('penalty',c.logistic_penalties)}
                    pred = fit_predict(logistic(**p,seed=c.tuning_seed,config=c),X,target,fold.inner_train,val)
                    elapsed = time.perf_counter()-start
                    timing_rows.append({'horizon':h,'fold':fold.number,'trial':trial.number,'seconds':elapsed})
                    return brier(target.iloc[val].to_numpy(),pred)
                with threadpool_limits(limits=1):
                    cap = None if smoke else yaml.safe_load((ROOT/c.timing_caps_path).read_text())['logistic'][str(h)]
                    study.optimize(objective,n_trials=c.smoke_trials if smoke else c.trials,timeout=cap)
                params = study.best_params
                for trial in study.trials: tuning_rows.append({'horizon':h,'fold':fold.number,'trial':trial.number,'brier':trial.value,**trial.params})
            for seed in c.evaluation_seeds:
                if seed == c.tuning_seed: raise ValueError('Tuning seed excluded from evaluation')
                candidates = [(m,w) for m in c.models for w in (c.window_days if m in ('trailing','recency') else [None])]
                inner_paths = {}; metadata = {}
                for name,window in candidates:
                    tag = name if window is None else f'{name}_{window}d'
                    filename = f'{tag}_{kind}_h{h}_fold{fold.number}_seed{seed}.parquet'
                    with threadpool_limits(limits=1):
                        p = fit_predict(logistic(**params,seed=seed,config=c),X,target,fold.inner_train,val) if name == 'logistic' else baseline(name,y,val,fold.inner_end,h,kind,window,c)
                    table = pd.DataFrame({'row_time':y.index[val],'origin':y.index[val]+pd.Timedelta(hours=c.issuance_offset_h),'y':target.iloc[val].to_numpy(),'p':p,'seed':seed})
                    path = output/'predictions/innerval'/filename; write_predictions(path,table,key)
                    inner_paths[tag] = path; metadata[tag] = (name,window,filename)
                chosen = {}
                for family in c.models:
                    choices = {tag:path for tag,path in inner_paths.items() if metadata[tag][0] == family}
                    chosen[family],_ = select(choices,output,key,c.selection_tolerance)
                strongest,scores = select({tag:inner_paths[tag] for tag in chosen.values()},output,key,c.selection_tolerance)
                selection_rows.append({'horizon':h,'fold':fold.number,'seed':seed,'strongest':strongest,'trailing':chosen['trailing'],'recency':chosen['recency'],'scores':json.dumps(scores)})
                thresholds = {tag:threshold(path,output,key) for tag,path in inner_paths.items()}
                guard.phase = 'evaluation'; test = guard.access(); test = test[target.iloc[test].notna().to_numpy()]
                predictions = {}
                for tag,(name,window,filename) in metadata.items():
                    with threadpool_limits(limits=1):
                        p = fit_predict(logistic(**params,seed=seed,config=c),X,target,fold.train,test) if name == 'logistic' else baseline(name,y,test,fold.train_end,h,kind,window,c)
                    table = pd.DataFrame({'row_time':y.index[test],'origin':y.index[test]+pd.Timedelta(hours=c.issuance_offset_h),'y':target.iloc[test].to_numpy(),'p':p,'seed':seed,'threshold':thresholds[tag]})
                    write_predictions(output/'predictions'/filename,table,key); predictions[tag] = table
                for family,tag in chosen.items():
                    table = predictions[tag]; truth = table.y.to_numpy(); probability = table.p.to_numpy()
                    metrics_rows.append({'model':family,'candidate':tag,'horizon':h,'fold':fold.number,'seed':seed,'n':len(table),'threshold':thresholds[tag],**classification(truth,probability,thresholds[tag],c),'bss_clim':bss(truth,probability,predictions['climatology'].p.to_numpy()),'bss_strong':bss(truth,probability,predictions[strongest].p.to_numpy())})
                    all_test.setdefault((h,family),[]).append(table.assign(fold=fold.number))
                all_ref.setdefault(h,[]).append(predictions['climatology']); all_strong.setdefault(h,[]).append(predictions[strongest])
    pd.DataFrame(metrics_rows).to_csv(output/'metrics/folds.csv',index=False)
    pd.DataFrame(selection_rows).to_csv(output/'metrics/selection.csv',index=False)
    pd.DataFrame(tuning_rows).to_csv(output/'metrics/tuning.csv',index=False)
    pd.DataFrame(timing_rows).to_csv(output/'metrics/timing.csv',index=False)
    pooled = []; intervals = []; lengths = []
    for (h,model),tables in all_test.items():
        frame = pd.concat(tables); ref = pd.concat(all_ref[h]); strong = pd.concat(all_strong[h]); truth = frame.y.to_numpy(); p = frame.p.to_numpy()
        pooled.append({'model':model,'horizon':h,'n':len(frame),'brier':brier(truth,p),'bss_clim':bss(truth,p,ref.p.to_numpy()),'bss_strong':bss(truth,p,strong.p.to_numpy())})
        reliability(truth,p,c.ece_bins).to_csv(output/f'metrics/reliability_{model}_h{h}.csv',index=False)
        losses = np.c_[(truth-p)**2,(truth-strong.p.to_numpy())**2]; months = frame.row_time.dt.month.to_numpy()
        length = block_length(losses[:,0]-losses[:,1],months,c); lengths.append({'model':model,'horizon':h,'block_h':length})
        result = bootstrap(losses,months,lambda a: np.mean(a[:,0]-a[:,1]),length,B=c.smoke_B if smoke else c.bootstrap_B,config=c)
        intervals.append({'model':model,'horizon':h,'comparison':'implemented strongest baseline','statistic':'dBS',**result})
        result = bootstrap(losses,months,lambda a: 1-a[:,0].sum()/a[:,1].sum(),length,B=c.smoke_B if smoke else c.bootstrap_B,method='bca',config=c)
        intervals.append({'model':model,'horizon':h,'comparison':'implemented strongest baseline','statistic':'BSS',**result})
    pooled = pd.DataFrame(pooled); pooled.to_csv(output/'metrics/pooled.csv',index=False)
    pd.DataFrame(intervals).to_csv(output/'inference/exploratory_intervals.csv',index=False)
    pd.DataFrame(lengths).to_csv(output/'inference/block_lengths.csv',index=False)
    ranks = {}
    folds_table = pd.DataFrame(metrics_rows)
    for h,group in folds_table.groupby('horizon'):
        table = group.pivot_table(index='fold',columns='model',values='brier'); ranks[str(h)] = {'models':list(table.columns),**descriptive_ranks(table.to_numpy(),c.alpha)}
    (output/'inference/descriptive_ranks.json').write_text(json.dumps(ranks,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax = plt.subplots()
    for model,group in pooled.groupby('model'): ax.plot(group.horizon,group.brier,marker='o',label=model)
    ax.set(xlabel='Horizon (h)',ylabel='Brier score',title='Harness smoke only; consumption-derived labels'); ax.legend(fontsize='small'); fig.tight_layout(); fig.savefig(output/'figures/brier.png'); plt.close(fig)
    saved = pd.read_csv(output/'metrics/pooled.csv'); audit = pd.read_csv(output/'data_audit.csv').iloc[0]
    (output/'README.md').write_text('# Harness smoke results - NOT the benchmark\n\nLabels are inferred from metered consumption. The hour convention remains unverified. These results do not clear the leakage gate or support scientific claims.\n\n'+f"Generated {len(saved)} pooled metric rows for {saved.model.nunique()} reference model families and {saved.horizon.nunique()} horizons. Label disagreement hours: {int(audit.disagreement_hours)}.\n\n"+'Read metrics/pooled.csv, metrics/folds.csv and inference/exploratory_intervals.csv. Strongest baseline selection uses saved inner-validation predictions; the baseline pool is incomplete. See DEVIATIONS.md for the missing calendar and unresolved hour convention. Reproduce with `python experiments/s1_wp2_smoke.py`.\n')
    return pooled

