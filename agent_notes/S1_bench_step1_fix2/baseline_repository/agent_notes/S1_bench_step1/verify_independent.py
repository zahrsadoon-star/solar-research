"""Audit frozen forecasts and bootstrap seed sensitivity without model refitting."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CHECK = ROOT / 'studies/S1_outage_forecasting/benchmark/significance_check'


def main() -> None:
    """Save dimensionless metric differences and class shares for every case."""
    spec = importlib.util.spec_from_file_location('independent', CHECK / 'check.py')
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    frame = pd.read_csv(check.INPUT)
    config = json.loads((CHECK / 'config.json').read_text())
    original, _ = check.analyze(frame, config)
    alternate, _ = check.analyze(frame, dict(config, seed=43))
    alternate.to_csv(HERE / 'seed43_pairs.csv', index=False)
    saved = pd.read_csv(CHECK / 'pairs.csv')
    numeric = original.select_dtypes(include='number').columns
    np.testing.assert_allclose(original[numeric], saved[numeric], atol=1e-10, rtol=1e-9)
    scores = pd.read_csv(CHECK.parent / 'results/benchmark_results.csv')
    metrics = []
    classes = []
    for site, h, g, names in check.validate(frame, config['cases']):
        for name in names:
            published = scores[(scores.site == site) & (scores.h == h) & (scores.algorithm == name)].iloc[0]
            for metric, value in [('brier', ((g[name]-g.y)**2).mean()),
                                  ('auc', check.auc(g.y.to_numpy(), g[name].to_numpy()))]:
                metrics.append(dict(site=site, h=h, algorithm=name, metric=metric,
                                    recomputed=value, published=published[metric],
                                    difference=value-published[metric]))
        for month, month_rows in g.groupby(pd.to_datetime(g.time).dt.month):
            classes.append(dict(site=site, h=h, month=month, n=len(month_rows),
                                outage_share=month_rows.y.mean()))
    pd.DataFrame(metrics).to_csv(HERE / 'original_metric_audit.csv', index=False)
    pd.DataFrame(classes).to_csv(HERE / 'original_class_shares.csv', index=False)
    intervals = ['brier_ci_low', 'brier_ci_high', 'auc_ci_low', 'auc_ci_high']
    summary = dict(columns=frame.columns.tolist(), seed42_reproduced=True,
        primary_seed=42, sensitivity_seed=43, resamples_each=config['resamples'],
        changed_pair_decisions=int((original.a_better != alternate.a_better).sum()),
        max_interval_endpoint_change={c: float((original[c]-alternate[c]).abs().max()) for c in intervals},
        max_absolute_published_metric_difference=pd.DataFrame(metrics).groupby('metric').difference.apply(lambda s: float(s.abs().max())).to_dict(),
        class_share_min=float(pd.DataFrame(classes).outage_share.min()),
        class_share_max=float(pd.DataFrame(classes).outage_share.max()))
    (HERE / 'independent_audit.json').write_text(json.dumps(summary, indent=2)+'\n')
    report = f"""# Statistical verification of the independent S1 check

## Verified calculations and seed sensitivity

The existing independent implementation was reviewed without reading, importing,
or executing main's significance.py. The original prediction columns are
{', '.join(frame.columns)}. There are six populated algorithms per case and no
reference predictions; all fifteen unordered pairs per case are included.

Recomputed the entire analysis with 2000 moving-block bootstrap draws at each of
seeds 42 and 43. Seed 42 reproduces every saved numeric pair result within CSV
serialization precision. Seed 43 changes {summary['changed_pair_decisions']} pair
decisions. Maximum absolute endpoint changes (dimensionless) are
{json.dumps(summary['max_interval_endpoint_change'])}.
These runs assess bootstrap Monte Carlo sensitivity only, not independent model
training variability. No models were refitted and no settings were tuned.

Original-export Brier and AUC values were recomputed against the published rounded
benchmark table. Maximum absolute differences are
{json.dumps(summary['max_absolute_published_metric_difference'])}; detailed
values are in original_metric_audit.csv. Treat these as comparisons between saved
rounded predictions and published metrics, not proof of bitwise training replay.

## Leakage and class imbalance

Four new parameterized tests in tests/test_s1_sig_check.py verify original-export
labels against raw data at time+h, strict training-target-before-test boundaries,
both classes in every monthly train/test fold, training-only StandardScaler
moments, and invariance of earlier features under perturbing future observations.
All passed. Source inspection confirms scalers are in sklearn pipelines fitted
on the training fold. Features include completed-origin-hour readings; this
availability assumption remains essential. These checks do not reconstruct the
historical cloud execution. Random-split results are nonprospective; MLP internal
early stopping uses a random validation subset within its outer training set.

Monthly test outage prevalence ranges from {summary['class_share_min']:.8f} to
{summary['class_share_max']:.8f}; original_class_shares.csv records every case/month.
The benchmark uses no explicit class weights or class resampling. Probability
losses retain the observed prevalence; bootstrap rows preserve temporal clusters
and are not class balanced. AUC measures ranking, while Brier reflects calibration
and prevalence. Accuracy alone is inadequate under imbalance. Every observed
fold has both classes; the checker returns unavailable AUC intervals if a bootstrap
replicate loses a class, rather than silently discarding draws.

## Statistical assumptions and interpretation

Verified paired noncircular moving blocks of 24 hours, percentile 95% intervals,
Bartlett Newey-West HAC lag h-1+24, HLN correction and two-sided Student t p-values,
and Holm over all fifteen comparisons within each case. Tests independently check
HAC through a covariance matrix, identical forecasts, a clear advantage, seeded
bootstrap reproducibility, tied AUC scores and a hand-computed Holm example.
Holm permits dependent tests but cannot repair inaccurate marginal p-values.
Pooled seasonal data, shared training sets and monthly refitting challenge weak
stationarity assumptions; dependence beyond 24 hours is not excluded. HLN is an
approximate finite-sample correction. No methodological sources were verified
offline and no citations were invented.

COMPARISON.md agrees with main's top-group membership in three cases. BG 1 h keeps
Gradient Boosting (Holm p about 0.134812 versus main's 0.04801). Main uses longer
blocks, a different HAC lag at h=6, no HLN and five best-versus-other tests rather
than fifteen all-pair tests. The effects of these changes were not individually
isolated. Non-rejection is not equivalence. Shortlists were selected on test scores;
this is exploratory within-case correction, not study-wide confirmatory inference.
Main README's equivalence and proven-winner language is not supported by these tests.

## Integration and validation limitations

The merge was attempted again and failed creating ORIG_HEAD.lock in shared Git
metadata outside the writable repository. All specified main files were freshly
verified byte-for-byte against local origin/main without inspecting significance.py.
The archived Windows drift remains accepted as cross-platform variability under
the lead decision; REPRO_NOTE.md records metric maxima and rank changes.

Ran python -m pytest -q with only the obsolete historical-disabled-entry-point test
excluded through PYTEST_ADDOPTS, to avoid executing main and overwriting artifacts.
Result: 65 passed, 4 failed, 1 skipped, 1 deselected, 58 warnings. The four failures
are old tests using the pre-move predictions path. The skipped test also uses that
path. All eleven independent-check tests passed. An unfiltered passing suite is
not claimed. The already prepared pending_test_update.patch needs an exception to
the allowed-file list. No commit, push, package installation or network access.

Reproduce this audit: python agent_notes/S1_bench_step1/verify_independent.py.
Machine-readable outputs and the alternate-seed pairs are in the same directory.
These are audit artifacts, not manuscript results.
"""
    (ROOT / 'agent_notes/STATS_REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
