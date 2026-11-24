"""Generate fixer documentation from saved results; no model fitting."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET


def main() -> None:
    """Write factual summaries with dimensionless metric differences and test counts."""
    here = Path(__file__).resolve().parent
    results = here / "results"
    notes = here.parents[3] / "agent_notes/S1_bench_verify"
    summary = json.loads((results / "comparison_summary.json").read_text())
    seed = json.loads((results / "seed_run.json").read_text())
    suites = ET.parse(results / "pytest_fixer.xml").getroot().findall("testsuite")
    counts = {key: sum(int(s.attrib[key]) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    (results / "fixer_checks.json").write_text(json.dumps(counts, indent=2) + "\n")
    findings = f"""Verdict: **{summary['verdict']}**. {summary['passed']} of {summary['comparisons']} prescribed comparisons pass.
The maximum original forest metric difference is {summary['max_abs_diff_by_method']['RF']:.8f}; its cause remains unresolved.
The extra seed check has maximum metric difference {seed['max_abs_diff']:.8f}; minority-class F1 is seed sensitive.
These are numerical tolerance and descriptive sensitivity checks, with no significance test or superiority claim.
Fresh tests: {counts['tests']} outcomes, {counts['failures']} failures, {counts['errors']} errors, {counts['skipped']} skips.
"""
    readme = """# Benchmark verification artifacts

The independent experiment loads the specified raw BG and KR workbooks, audits energy and outage shares,
constructs every enumerated causal predictor, and evaluates the prescribed references, logistic regression
and random forest with expanding monthly training and pooled chronological test predictions.
The original independent implementation was frozen before benchmark source inspection. The fixer extends
that existing work; it is not a newly blinded implementation. No model was refitted during the fixer pass.

""" + findings + """
## Reproduce from repository root (existing environment, no installation)

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py compare
python studies/S1_outage_forecasting/benchmark/verify/statistical_review.py report
python -m pytest -q tests studies/S1_outage_forecasting/benchmark/verify/tests -o cache_dir=agent_notes/S1_bench_verify/pytest_cache --basetemp=agent_notes/S1_bench_verify/pytest_fixer_tmp --junitxml=studies/S1_outage_forecasting/benchmark/verify/results/pytest_fixer.xml
python studies/S1_outage_forecasting/benchmark/verify/document_fixes.py
```

To refit independently, choose a previously unused name:

```powershell
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py independent --run-name replication
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py compare --run-name replication
```

Named runs write beneath `runs/`; nonempty directories are rejected. The original run remains here.
Comparison verifies the producing source snapshot, current config and raw input hashes, frozen output hashes,
and complete unique case grids on both sides. A changed current verifier is permitted because comparison
validates the preserved producing source, not a claim that the current script produced the old outputs.
Named runs save their producing source alongside their manifest. The report command describes the original run.
The existing additional-seed artifacts are preserved; `statistical_review.py run` overwrites those derived
seed artifacts and should not be used when preserving that evidence is required.

## Files and limitations

`freeze.json` records original configuration, seeds, software, runtime and hashes. `predictions.csv` and
`independent_metrics.csv` hold pooled predictions and metrics. `data_audit.csv`, `outage_shares.csv`,
`exclusions.csv` and `folds.csv` document loading and eligibility. `comparison.csv` contains every metric
comparison. `leakage_audit.csv` and `random_split_audit.csv` support the audit. `seed_stability.csv` and
`seed_run.json` describe the extra seed. `pytest_fixer.xml` and `fixer_checks.json` record fresh tests.
See ../REPORT.md and the task-notes STATS_REPORT.md for detailed findings.

No chronological leakage was found, conditional on completed origin-hour metering being available.
Random holdout is non-prospective; its entire uplift cannot be attributed to adjacent hours.
The feature enumeration exceeds the README's stated count; all enumerated features were retained.
The limited seed check cannot establish robustness. Proxy labels, unknown metering latency, seasonal
dependence, class imbalance, limited households, data permissions and citation evidence remain weaknesses.
No tuning was introduced, and shared features do not establish equal tuning budgets across algorithms.
Publication corrections to the parent benchmark README require a separately authorized revision.
"""
    (results / "README.md").write_text(readme, encoding="utf-8")
    report = """# Fixer and documenter report

The review lists no blocking MUST-FIX. Its pre-publication README corrections are explicitly deferred
to a separately authorized benchmark revision, outside this task's write allowlist.
Resolved the actionable comparison-completeness and original-freeze preservation SHOULD-FIX items.
Missing, duplicate, unexpected or nonfinite metric cases now fail explicitly on either comparison side.
Independent runs reject nonempty output directories and support named runs with producing-source snapshots.
Comparison checks source/config/input/output provenance before reading benchmark values.
No experiment rerun was necessary: estimator, feature, split and metric computations are unchanged.
Original frozen outputs and extra-seed evidence were preserved; comparison and documentation were regenerated.

""" + findings + """
Files touched in this pass:
- verify/verify_benchmark.py: comparison and rerun safeguards; reproduction instructions.
- verify/tests/test_s1_bench_verify.py: regression checks for incomplete cases, provenance and overwrite rejection.
- verify/document_fixes.py: generated documentation and test summary.
- verify/REPORT.md and derived comparison/audit/report artifacts: regenerated from preserved evidence.
- verify/results/README.md, pytest_fixer.xml and fixer_checks.json: documentation and fresh validation.
- agent_notes/S1_bench_verify/FIX_REPORT.md, CODEX_REPORT.md and STATS_REPORT.md; permitted test cache/temp files.

Validation commands are recorded in verify/results/README.md. All repository tests and verifier tests ran.
Existing timedelta deprecation warnings persist. No tuning, installation, network, commit or push.
No protected benchmark source/results, raw data or legacy files were changed.

Open items: original RF discrepancy remains unexplained; original benchmark environment/predictions are
not supplied for causal investigation. Extra-seed sensitivity does not support robustness or superiority.
Publication feature-count/ranking/random-uplift wording, metering availability, citations and permissions
remain lead follow-ups. Tests and requested reports stay in verify/ and the task-specific notes directory,
following the explicit allowlist instead of the conflicting generic root report/test locations.
"""
    for name in ("FIX_REPORT.md", "CODEX_REPORT.md"):
        (notes / name).write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
