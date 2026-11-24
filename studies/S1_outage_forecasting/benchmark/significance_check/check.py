"""Independent frozen-forecast check; run this file from any working directory.

All losses, effects, AUCs and probabilities are dimensionless. Time parameters
are hours on a validated consecutive hourly grid. No model code is imported.
"""
from __future__ import annotations

import hashlib
import io
import itertools
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.stats import rankdata, t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INPUT = HERE.parent / 'results/hourly_predictions_top6.csv.gz'
OUTPUT = HERE.parent / 'results/significance_check'
HISTORICAL_REVISION = 'cec3552'


def dm_test(d: np.ndarray, h: int) -> dict:
    """Test mean dimensionless Brier loss difference with HAC and HLN; h in hours."""
    d = np.asarray(d, dtype=float)
    n, lag = len(d), h - 1 + 24
    if d.ndim != 1 or h < 1 or n <= lag + 1 or not np.isfinite(d).all():
        raise ValueError('Invalid losses or insufficient observations for HAC lag')
    mean = float(d.mean())
    result = {'brier_diff': mean, 'hac_lag': lag, 'dm_stat': np.nan, 'p_value': np.nan,
                  'long_run_variance': np.nan, 'dm_status': 'invalid_variance'}
    if np.all(d == 0):
        return dict(result, dm_stat=0., p_value=1., long_run_variance=0., dm_status='identical')
    z = d - mean
    variance = float(z @ z / n)
    for k in range(1, lag + 1):
        variance += 2 * (1 - k / (lag + 1)) * float(z[k:] @ z[:-k]) / n
    result['long_run_variance'] = variance
    if not np.isfinite(variance) or variance <= 0 or np.ptp(d) == 0:
        return result
    correction = np.sqrt((n + 1 - 2*h + h*(h-1)/n) / n)
    statistic = mean / np.sqrt(variance / n) * correction
    return dict(result, dm_stat=float(statistic), p_value=float(2*t.sf(abs(statistic), n-1)),
                dm_status='ok')


def holm(p: np.ndarray) -> np.ndarray:
    """Within-family Holm probabilities; invalid tests count conservatively as one."""
    p = np.asarray(p, dtype=float)
    safe = np.where(np.isfinite(p), p, 1.)
    if np.any((safe < 0) | (safe > 1)):
        raise ValueError('Probabilities must lie in [0, 1]')
    order = np.argsort(safe, kind='stable')
    adjusted = np.empty(len(p))
    adjusted[order] = np.minimum(1., np.maximum.accumulate(safe[order] * np.arange(len(p), 0, -1)))
    return adjusted


def block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Sample noncircular overlapping blocks; n and block are hourly row counts."""
    if not 1 <= block <= n:
        raise ValueError('Block must fit the series')
    starts = rng.integers(0, n-block+1, size=(n+block-1)//block)
    return (starts[:, None] + np.arange(block)).ravel()[:n]


def auc(y: np.ndarray, p: np.ndarray) -> float:
    """Dimensionless pooled AUC with average ranks for ties; NaN for one class."""
    positives = y == 1
    n1, n0 = int(positives.sum()), int((y == 0).sum())
    if not n1 or not n0:
        return float('nan')
    return float((rankdata(p)[positives].sum() - n1*(n1+1)/2) / (n1*n0))


def bootstrap(y: np.ndarray, probabilities: np.ndarray, *, block: int = 24,
              resamples: int = 2000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Paired moving-block draws of Brier and AUC, shape (replicates, algorithms)."""
    rng = np.random.default_rng(seed)
    losses = (probabilities - y[:, None])**2
    bs = np.empty((resamples, probabilities.shape[1]))
    au = np.empty_like(bs)
    for r in range(resamples):
        indices = block_indices(len(y), block, rng)
        bs[r] = losses[indices].mean(axis=0)
        for j in range(probabilities.shape[1]):
            au[r, j] = auc(y[indices], probabilities[indices, j])
    return bs, au


def validate(frame: pd.DataFrame, cases: list) -> list[tuple[str, int, pd.DataFrame, list[str]]]:
    """Validate complete, aligned hourly forecasts without pair-specific deletion."""
    metadata = {'site', 'h', 'time', 'y'}
    if not metadata.issubset(frame.columns):
        raise ValueError('Missing metadata columns')
    if frame.duplicated(['site', 'h', 'time']).any():
        raise ValueError('Duplicate forecast keys')
    if set(frame.groupby(['site', 'h']).groups) != {tuple(c) for c in cases}:
        raise ValueError('Unexpected case coverage')
    groups = []
    for (site, h), g in frame.groupby(['site', 'h'], sort=True):
        g = g.sort_values('time').copy()
        times = pd.to_datetime(g.time, errors='raise')
        if times.isna().any() or not times.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all():
            raise ValueError('Nonconsecutive hourly timestamps')
        if not g.y.isin([0, 1]).all():
            raise ValueError('Nonbinary labels')
        names = []
        for name in frame.columns.difference(list(metadata)):
            if g[name].isna().all():
                continue
            values = g[name].to_numpy(dtype=float)
            if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
                raise ValueError('Partial missingness or invalid probability')
            names.append(name)
        if len(names) != 6:
            raise ValueError('Expected six complete algorithms, with no reference column')
        names.sort(key=lambda name: (float(((g[name]-g.y)**2).mean()), name))
        groups.append((str(site), int(h), g, names))
    return groups


def interval(values: np.ndarray, alpha: float) -> tuple[float, float]:
    """Marginal percentile interval; any undefined replicate makes it unavailable."""
    if not np.isfinite(values).all():
        return float('nan'), float('nan')
    lo, hi = np.quantile(values, [alpha/2, 1-alpha/2], method='linear')
    return float(lo), float(hi)


def analyze(frame: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Calculate all unordered Brier-ranked pairs and case provenance."""
    rows, case_metadata = [], []
    for site, h, g, names in validate(frame, config['cases']):
        y, p = g.y.to_numpy(), g[names].to_numpy()
        losses = (p-y[:, None])**2
        bs, au = bootstrap(y, p, block=config['block_hours'],
                           resamples=config['resamples'], seed=config['seed'])
        pooled_auc = [auc(y, p[:, j]) for j in range(len(names))]
        case_rows = []
        for i, j in itertools.combinations(range(len(names)), 2):
            blo, bhi = interval(bs[:, i]-bs[:, j], config['alpha'])
            alo, ahi = interval(au[:, i]-au[:, j], config['alpha'])
            valid = int(np.isfinite(au[:, i]-au[:, j]).sum())
            case_rows.append(dict(site=site, h=h, algorithm_a=names[i], algorithm_b=names[j],
                rank_a=i+1, rank_b=j+1, n=len(y), brier_a=float(losses[:, i].mean()),
                brier_b=float(losses[:, j].mean()), **dm_test(losses[:, i]-losses[:, j], h),
                brier_ci_low=blo, brier_ci_high=bhi, auc_a=pooled_auc[i], auc_b=pooled_auc[j],
                auc_diff=pooled_auc[i]-pooled_auc[j], auc_ci_low=alo, auc_ci_high=ahi,
                auc_valid_resamples=valid, auc_status='ok' if valid == config['resamples'] else 'undefined_replicate',
                seed=config['seed'], resamples=config['resamples'], block_hours=config['block_hours']))
        adjusted = holm(np.array([r['p_value'] for r in case_rows]))
        for row, padj in zip(case_rows, adjusted):
            row['p_holm'] = float(padj)
            row['a_better'] = bool(padj < config['alpha'] and row['brier_ci_high'] < 0)
        rows.extend(case_rows)
        case_metadata.append({'site': site, 'h': h, 'n': len(g), 'origin_start': str(g.time.iloc[0]),
            'origin_end': str(g.time.iloc[-1]),
            'target_start': str(pd.Timestamp(g.time.iloc[0])+pd.Timedelta(hours=h)), 'target_end': str(pd.Timestamp(g.time.iloc[-1])+pd.Timedelta(hours=h)),
            'ranking': names})
        print(f'{site} h={h}: {len(case_rows)} pairs', flush=True)
    return pd.DataFrame(rows), case_metadata


def comparison(pairs: pd.DataFrame, primary: pd.DataFrame) -> str:
    """Compare groups after independent computation, using primary CSV flags."""
    lines = ['# Independent significance check', '',
        ('Historical comparator: `cec3552`; current local main is recorded separately in '
        '`../results/significance_check/manifest.json`. Non-rejection is not equivalence.'), '',
        '| Case | Independent top group | cec3552 top group | Finding and evidence |',
        '|---|---|---|---|']
    for (site, h), g in pairs.groupby(['site', 'h']):
        best_rows = g[g.rank_a == 1]
        best = best_rows.algorithm_a.iloc[0]
        ours = [best] + best_rows.loc[~best_rows.a_better, 'algorithm_b'].tolist()
        main = primary[(primary.site == site) & (primary.h == h)]
        if len(main) != 5 or set(main.best) != {best} or set(main.other) != set(best_rows.algorithm_b):
            raise ValueError('Primary comparison coverage mismatch')
        excluded = main.best_really_better.astype(str).str.lower().eq('true')
        theirs = [best] + main.loc[~excluded, 'other'].tolist()
        changes = sorted(set(ours) ^ set(theirs))
        evidence = []
        for name in changes:
            row = best_rows[best_rows.algorithm_b == name].iloc[0]
            original = main[main.other == name].iloc[0]
            evidence.append(
                f'{name}: check Holm p={row.p_holm:.6g}, Brier CI '
                f'[{row.brier_ci_low:.6g}, {row.brier_ci_high:.6g}]; '
                f'historical Holm p={original.p_holm:.6g}, sign-normalized CI '
                f'[{-original.brier_diff_ci_high:.6g}, {-original.brier_diff_ci_low:.6g}]')
        rf_et = g[(g.algorithm_a.isin(['Random Forest', 'Extra Trees'])) &
                  (g.algorithm_b.isin(['Random Forest', 'Extra Trees']))].iloc[0]
        evidence.append(f'RF/Extra Trees Holm p={rf_et.p_holm:.6g}, Brier CI '
                        f'[{rf_et.brier_ci_low:.6g}, {rf_et.brier_ci_high:.6g}]; '
                        f'exclusion rule {"met" if rf_et.a_better else "not met"}')
        unresolved = best_rows.loc[~best_rows.dm_status.isin(['ok', 'identical']), 'algorithm_b'].tolist()
        finding = 'differ' if changes else 'agree: same competitors survive the joint exclusion rule'
        lines.append(f'| {site}, {h} h | {"; ".join(ours)} | {"; ".join(theirs)} | '
                     f'{finding}; {"; ".join(evidence)}; unresolved: {", ".join(unresolved) or "none"} |')
    lines += ['', '## Interpretation and reproducibility', '',
        ('Groups contain the descriptive lowest-Brier algorithm and competitors not excluded '
        'by both Holm p < 0.05 and a strictly negative upper Brier interval. This does not '
        'establish equivalence or pairwise equality. Invalid comparisons remain unresolved. '
        'Effects are A minus B: negative Brier favors A; positive AUC favors A. Historical '
        'Brier effects are other minus best and are sign-normalized above.'), '',
        ('The check uses paired noncircular 24-hour blocks, 2000 draws, seed 42 reset per case, '
        'linear percentile 95% marginal intervals, Bartlett HAC lag h-1+24, horizon-based '
        'HLN correction, two-sided Student t with N-1 degrees of freedom, and Holm over all '
        '15 pairs within each case. cec3552 uses 168-hour blocks, fixed HAC lag 24, no HLN '
        'correction, and Holm over five best-versus-other comparisons. These choices differ '
        'jointly; no membership change is attributed to one choice without isolating it. '
        'No across-case error control is claimed.'), '',
        ('Only frozen hourly_predictions_top6.csv.gz supplies forecasts. Reference probabilities '
        '(no-outage, persistence, seasonal) are absent; reference significance comparisons '
        'are unavailable. No superiority over those baselines is claimed. The core frozen-forecast '
        'check performs no refitting or settings search. A supplementary exploratory audit '
        'refits RF and Extra Trees for April only, both sites/horizons, seeds 42/43. This '
        'deviates from the original no-refitting protocol (documented in agent_notes/PLAN.md); '
        'its selection is not established as prespecified. The saved full-benchmark training '
        'seed is 42; bootstrap replicates are not independent training runs. The April subset '
        'does not meet the full-benchmark multiple-run requirement; both models have zero '
        'April KR recall at both horizons and seeds. The supplementary bootstrap-seed audit '
        'checks same-implementation replay and Monte Carlo stability, not independent '
        'implementation correctness or block-length/HAC sensitivity.'), '',
        ('Run `python studies/S1_outage_forecasting/benchmark/significance_check/check.py`. '
        'Config is beside the script; CSV, JSON and figure outputs are under '
        '`../results/significance_check/`. The manifest records source revision, input hash, '
        'software versions, case sizes and origin/target ranges.'), '',
        ('Origins are completed hourly observations; the target is grid_kwh at t+h equal to '
        'zero, a metering proxy. Evaluation is April-December 2018 with expanding monthly '
        'training, excluding training labels reaching the test month. The export alone '
        'cannot establish training provenance. Leakage tests audit source behavior separately.'), '',
        ('This is exploratory: shortlists were test-selected and primary results already seen. '
        'Limitations include dependence beyond 24 hours, seasonal nonstationarity, shared '
        'training sets, monthly model changes, one training seed, rounded probabilities, '
        'proxy-label error, uncertain metering latency, class imbalance, unequal tuning '
        'budgets and one year per household. Separate models do not demonstrate geographic '
        'transfer. Methodological citations remain [UNVERIFIED] offline. The accepted '
        'Windows/Linux drift interpretation was not causally isolated.'), '']
    return '\n'.join(lines)


def plot_pairs(pairs: pd.DataFrame) -> None:
    """Plot dimensionless best-minus-competitor Brier effects and marginal intervals."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for ax, ((site, h), group) in zip(axes.flat, pairs.groupby(['site', 'h'])):
        rows = group[group.rank_a == 1]
        positions = np.arange(len(rows))
        ax.hlines(positions, rows.brier_ci_low, rows.brier_ci_high)
        ax.scatter(rows.brier_diff, positions)
        ax.axvline(0, color='grey', linestyle='--')
        ax.set_yticks(positions, rows.algorithm_b)
        ax.set_title(f'{site}, {h} h: best = {rows.algorithm_a.iloc[0]}')
        ax.set_xlabel('Best minus competitor Brier (95% marginal CI)')
    fig.savefig(OUTPUT / 'brier_intervals.png', dpi=150)
    plt.close(fig)


def main() -> None:
    """Write independent pair results, comparison and machine-readable provenance."""
    config_path = HERE / 'config.json'
    config = json.loads(config_path.read_text())
    pairs, cases = analyze(pd.read_csv(INPUT), config)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(OUTPUT / 'pairs.csv', index=False, float_format='%.12g')
    primary_path = HERE.parent / 'results/significance.csv'
    primary_bytes = subprocess.check_output(
        ['git', 'show', HISTORICAL_REVISION + ':' + primary_path.relative_to(ROOT).as_posix()], cwd=ROOT)
    primary = pd.read_csv(io.BytesIO(primary_bytes))
    plot_pairs(pairs)
    (HERE / 'COMPARISON.md').write_text(comparison(pairs, primary), encoding='utf-8')
    manifest = {'config': config, 'cases': cases, 'reference': 'absent; inference unavailable',
        'input': str(INPUT.relative_to(ROOT)), 'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        'primary_sha256': hashlib.sha256(primary_bytes).hexdigest(),
        'historical_revision': subprocess.check_output(['git', 'rev-parse', HISTORICAL_REVISION], cwd=ROOT, text=True).strip(),
        'input_source_revision': subprocess.check_output(['git', 'log', '-1', '--format=%H', 'main', '--', INPUT.relative_to(ROOT).as_posix()], cwd=ROOT, text=True).strip(),
        'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'local_main': subprocess.check_output(['git', 'rev-parse', 'main'], cwd=ROOT, text=True).strip(),
        'python': platform.python_version(), 'platform': platform.platform(), 'numpy': np.__version__,
        'pandas': pd.__version__, 'scipy': scipy.__version__,
        'integration': integration_status()}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


def integration_status() -> dict:
    """Read actual Git ancestry and protected blob identity without executing them."""
    ancestry = subprocess.run(['git', 'merge-base', '--is-ancestor', 'main', 'HEAD'],
                              cwd=ROOT, capture_output=True, text=True, check=False)
    if ancestry.returncode not in (0, 1):
        raise RuntimeError(ancestry.stderr)
    base = 'studies/S1_outage_forecasting/benchmark/'
    paths = [base + name for name in ['README.md', 'benchmark.py', 'significance.py']]
    paths += subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', 'main', base + 'results/'],
        cwd=ROOT, text=True).splitlines()
    matches = {}
    for path in paths:
        expected = subprocess.check_output(['git', 'rev-parse', 'main:' + path],
                                           cwd=ROOT, text=True).strip()
        if not (ROOT / path).is_file():
            matches[path] = False
            continue
        actual = subprocess.check_output(['git', 'hash-object', '--no-filters', path],
                                         cwd=ROOT, text=True).strip()
        matches[path] = actual == expected
    return {'local_main_is_ancestor': ancestry.returncode == 0,
                'protected_blobs_match': matches}


if __name__ == '__main__':
    main()
