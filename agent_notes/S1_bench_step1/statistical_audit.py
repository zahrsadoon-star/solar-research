"""Audit saved hourly metrics without refitting after the failed preservation gate."""
import json
import subprocess
from pathlib import Path
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score
from check_preservation import compare
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'studies/S1_outage_forecasting/benchmark/results'

def main() -> None:
    """Write dimensionless metric differences and hourly class shares."""
    frozen = pd.read_csv(OUT / 'benchmark_results.csv')
    rerun = pd.read_csv(OUT / 'step1_rerun/benchmark_results.csv')
    gate = compare(frozen, rerun)
    p = pd.read_csv(OUT / 'predictions.csv.gz')
    metrics = dict(accuracy=accuracy_score, precision=precision_score, recall=recall_score,
                   f1=f1_score, auc=roc_auc_score, brier=brier_score_loss)
    differences = []
    for row in rerun.itertuples():
        case = p[(p.site == row.site) & (p.h == row.h)]
        for name, score in metrics.items():
            pred = case[row.algorithm]
            if name not in ('auc', 'brier'):
                pred = (pred >= 0.5).astype(int)
            kwargs = {'zero_division': 0} if name in ('precision', 'recall', 'f1') else {}
            delta = round(float(score(case.y, pred, **kwargs)), 4) - getattr(row, name)
            if abs(delta) > 1e-12:
                differences.append(dict(site=row.site, h=row.h, algorithm=row.algorithm, metric=name, difference=delta))
    restored, normalized, backups = {}, {}, {}
    for name in ('benchmark_results.csv', 'benchmark_fold_scores.csv', 'overall_ranking.csv', 'benchmark_accuracy.png'):
        path = OUT / name
        tracked = subprocess.check_output(['git', 'show', 'HEAD:' + path.relative_to(ROOT).as_posix()], cwd=ROOT)
        restored[name] = tracked == path.read_bytes()
        normalized[name] = tracked.replace(b'\r\n', b'\n') == path.read_bytes().replace(b'\r\n', b'\n')
        backups[name] = path.read_bytes() == (Path(__file__).parent / 'original_results' / name).read_bytes()
    p.groupby(['site', 'h', 'month']).y.agg(['size', 'sum', 'mean']).rename(
        columns={'size': 'test_hours', 'sum': 'outage_hours', 'mean': 'outage_share'}
    ).to_csv(OUT / 'step1_statistical_class_shares.csv')
    result = dict(preservation_passed=gate['passed'], changed_metric_cells=len(gate['differences']),
                  maximum_absolute_difference=gate['max_absolute_difference_by_metric'],
                  archived_rerun_metric_discrepancies=differences, original_artifacts_match_HEAD_bytes=restored,
                  original_artifacts_match_HEAD_normalized=normalized, original_artifacts_match_backup_bytes=backups, new_seed_run=False, stop_reason='Published metrics changed; task step 1 requires stopping.')
    (OUT / 'step1_statistical_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()

