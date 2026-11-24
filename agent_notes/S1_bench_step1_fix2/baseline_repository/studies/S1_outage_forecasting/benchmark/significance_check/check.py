"""Independent frozen-forecast check; run this file from any working directory.

All losses, effects, AUCs and probabilities are dimensionless. Time parameters
are hours on a validated consecutive hourly grid. No model code is imported.
"""
from __future__ import annotations

import hashlib
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


def dm_test(d: np.ndarray, h: int) -> dict:
    """Test mean dimensionless Brier loss difference with HAC and HLN; h in hours."""
    d = np.asarray(d, dtype=float)
    n, lag = len(d), h - 1 + 24
    if d.ndim != 1 or h < 1 or n <= lag + 1 or not np.isfinite(d).all():
        raise ValueError('Invalid losses or insufficient observations for HAC lag')
    mean = float(d.mean())
    result = dict(brier_diff=mean, hac_lag=lag, dm_stat=np.nan, p_value=np.nan,
                  long_run_variance=np.nan, dm_status='invalid_variance')
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
        case_metadata.append(dict(site=site, h=h, n=len(g), origin_start=str(g.time.iloc[0]),
            origin_end=str(g.time.iloc[-1]), target_end=str(pd.Timestamp(g.time.iloc[-1])+pd.Timedelta(hours=h)),
            ranking=names))
        print(f'{site} h={h}: {len(case_rows)} pairs', flush=True)
    return pd.DataFrame(rows), case_metadata


def comparison(pairs: pd.DataFrame, primary: pd.DataFrame) -> str:
    """Compare groups after independent computation, using primary CSV flags."""
    lines = ['# Independent significance check', '',
        'Non-rejection is not equivalence. Exploratory within-case Holm only; '
        'these groups do not establish pairwise equivalence or study-wide superiority.', '',
        '| Case | Independent top group | Main top group | Membership | Unresolved |',
        '|---|---|---|---|---|']
    differences = []
    for (site, h), g in pairs.groupby(['site', 'h']):
        best_rows = g[g.rank_a == 1]
        best = best_rows.algorithm_a.iloc[0]
        ours = [best] + best_rows.loc[~best_rows.a_better, 'algorithm_b'].tolist()
        main = primary[(primary.site == site) & (primary.h == h)]
        if len(main) != 5 or set(main.best) != {best} or set(main.other) != set(best_rows.algorithm_b):
            raise ValueError('Primary comparison coverage mismatch')
        excluded = main.best_really_better.astype(str).str.lower().eq('true')
        theirs = [best] + main.loc[~excluded, 'other'].tolist()
        unresolved = best_rows.loc[~best_rows.dm_status.isin(['ok', 'identical']), 'algorithm_b'].tolist()
        lines.append(f'| {site}, {h} h | {"; ".join(ours)} | {"; ".join(theirs)} | '
                     f'{"agree" if set(ours) == set(theirs) else "disagree"} | {"; ".join(unresolved) or "none"} |')
        for name in sorted(set(ours) ^ set(theirs)):
            independent = best_rows[best_rows.algorithm_b == name].iloc[0]
            published = main[main.other == name].iloc[0]
            differences.append(
                f'- {site}, {h} h, {name}: independent Holm p={independent.p_holm:.6g}, '
                f'best-minus-other Brier CI [{independent.brier_ci_low:.6g}, '
                f'{independent.brier_ci_high:.6g}]; main Holm p={published.p_holm:.6g}, '
                f'sign-normalized CI [{-published.brier_diff_ci_high:.6g}, '
                f'{-published.brier_diff_ci_low:.6g}]. '
                f'The competitor is {"retained" if name in ours else "excluded"} by this check.')
    lines += ['', '## Current-status correction', '',
        'This document supersedes the scientific-status guidance in the preserved '
        'benchmark/results/README.md: significance is no longer blocked by Windows '
        'preservation drift, and the original-run significance.csv and '
        'hourly_predictions_top6.csv.gz are the primary artifacts for this comparison. '
        'That README describes an obsolete preservation gate. The required Git merge '
        'is a separate integration requirement; see manifest.json for actual ancestry.', '',
        'The preserved benchmark/README.md claims statistical equivalence, calls bagged '
        'ensembles the best choice, and says Naive Bayes, Decision Tree, SVM and MLP '
        'are clearly behind. This check does not support those claims: non-rejection '
        'does not establish equivalence, and algorithms outside each saved shortlist '
        'were not tested. Its causal explanation of random-split improvement is also '
        'unproven; descriptive improvement does not isolate its cause. Primary documents '
        'are protected by the task; the lead must correct their wording separately.', '']
    lines += ['', '## Changed memberships', ''] + (differences or ['None.'])
    lines += ['', '## Interpretation and method differences', '',
        'Groups include the descriptive Brier best and competitors not excluded by both '
        'Holm p < 0.05 and a strictly negative upper Brier difference CI. '
        'Effects here are A minus B: negative Brier favors A; positive AUC favors A. '
        'Main reports other-minus-best Brier effects, the opposite orientation.', '',
        'This check uses paired noncircular 24 h blocks, 2000 draws, seed 42 reset per case, '
        'linear percentile 95% marginal intervals, HAC lag h-1+24, HLN correction with horizon h, '
        'a two-sided Student t reference with N-1 degrees of freedom, and Holm over all 15 pairs. '
        'Main uses 168 h blocks, fixed HAC lag 24, no HLN, and best-versus-others only '
        '(Holm over five tests). Main reports accuracy intervals; this check reports AUC intervals. '
        'These differences jointly explain why group membership can differ; no single change '
        'is causally isolated. Shorter blocks change interval widths and the larger Holm family '
        'changes rejection thresholds. Saved probability rounding can also affect estimates.', '',
        'The primary groups above are read from significance.csv and match the main benchmark '
        'README table (kNN denotes k-Nearest Neighbours). Its equivalence wording is not adopted here. '
        'No reference prediction column exists in the original export; reference comparisons are skipped.', '',
        '## Scope and reproducibility', '',
        'Run `python studies/S1_outage_forecasting/benchmark/significance_check/check.py`. '
        'Configuration is in config.json; manifest.json records hashes, revisions, software, '
        'sample sizes and time ranges. Only hourly_predictions_top6.csv.gz supplies predictions. '
        'No refitting or settings changes are performed. Bootstrap draws are not independent '
        'training runs; the saved benchmark has a single training seed (42).', '',
        'Time is interpreted as forecast-origin time, with target time time+h. The target is '
        'grid energy equal to zero at t+h, a metering proxy, not any outage over the interval. '
        'Completed-origin-hour metering is assumed available. The export cannot verify training '
        'provenance or absence of feature leakage. Shortlists were selected on the test set; '
        'prior exposure to primary results, temporal nonstationarity, dependence beyond 24 h, '
        'shared expanding training sets, monthly refitting, rounded probabilities, proxy-label '
        'error, metering latency, class imbalance and one year per household limit inference. '
        'Separate site models do not demonstrate geographic transfer. HLN is approximate. '
        'No methodological citations were verified offline.', '',
        'Common features and outer splits do not establish equal tuning budgets. '
        'Without reference forecasts, superiority over persistence or seasonal references '
        'remains untested. All inference is conditional on saved single-seed forecasts; '
        'bootstrap-seed sensitivity is not training-seed replication. Equal-budget tuning '
        'and feature ablations remain future work. Before publication, assess dependence '
        'beyond 24 hours and seasonal/monthly heterogeneity under a separately approved '
        'protocol, and verify methodological sources.', '']
    return '\n'.join(lines)


def main() -> None:
    """Write independent pair results, comparison and machine-readable provenance."""
    config_path = HERE / 'config.json'
    config = json.loads(config_path.read_text())
    pairs, cases = analyze(pd.read_csv(INPUT), config)
    pairs.to_csv(HERE / 'pairs.csv', index=False, float_format='%.12g')
    primary_path = HERE.parent / 'results/significance.csv'
    primary = pd.read_csv(primary_path)
    (HERE / 'COMPARISON.md').write_text(comparison(pairs, primary), encoding='utf-8')
    manifest = dict(config=config, cases=cases, reference='absent; skipped',
        input=str(INPUT.relative_to(ROOT)), input_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        primary_sha256=hashlib.sha256(primary_path.read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        origin_main=subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=ROOT, text=True).strip(),
        python=platform.python_version(), platform=platform.platform(), numpy=np.__version__,
        pandas=pd.__version__, scipy=scipy.__version__,
        integration=integration_status())
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


def integration_status() -> dict:
    """Read actual Git ancestry and protected blob identity without executing them."""
    ancestry = subprocess.run(['git', 'merge-base', '--is-ancestor', 'origin/main', 'HEAD'],
                              cwd=ROOT, capture_output=True, text=True)
    if ancestry.returncode not in (0, 1):
        raise RuntimeError(ancestry.stderr)
    base = 'studies/S1_outage_forecasting/benchmark/'
    paths = [base + name for name in ['README.md', 'benchmark.py', 'significance.py']]
    paths += subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', 'origin/main', base + 'results/'],
        cwd=ROOT, text=True).splitlines()
    matches = {}
    for path in paths:
        expected = subprocess.check_output(['git', 'rev-parse', 'origin/main:' + path],
                                           cwd=ROOT, text=True).strip()
        actual = subprocess.check_output(['git', 'hash-object', '--no-filters', path],
                                         cwd=ROOT, text=True).strip()
        matches[path] = actual == expected
    return dict(origin_main_is_ancestor=ancestry.returncode == 0,
                protected_blobs_match=matches)


if __name__ == '__main__':
    main()
