"""Verify nonfinite parameter provenance; probabilities/losses are dimensionless."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies/S1_outage_forecasting/benchmark'))
import tuning as tu  # noqa: E402


def main() -> None:
    """Save exact nonfinite parameter locations and strict-JSON checks under results/."""
    found = []
    for name in tu.SEARCH_SPACES:
        for i, config in enumerate(tu.configurations(name, 8)):
            model = tu.estimator(name, config, i)
            for key, value in model.get_params(deep=True).items():
                if isinstance(value, float) and not math.isfinite(value):
                    found.append({'algorithm': name, 'candidate': i,
                                  'parameter': key, 'value': repr(value)})
            json.dumps(tu.json_params(model), allow_nan=False)
    assert len(found) == 8
    assert all(r['algorithm'] == 'XGBoost' and r['parameter'] == 'missing' for r in found)
    log = Path('D:/SolarProject/logs/tuning_grid_20261122.err.log').read_text()
    notes = (ROOT / 'agent_notes/S1_bench_step2/NANFIX.md').read_text()
    assert log.strip() in notes
    out = (ROOT / 'studies/S1_outage_forecasting/benchmark/results/tuning'
           / 'statistical_audit/nanfix_root_cause.json')
    out.write_text(json.dumps({'nonfinite_parameters': found,
                              'all_96_parameter_documents_strict_json': True,
                              'original_traceback_matches_notes': True},
                             indent=2, allow_nan=False))
    print(out)


if __name__ == '__main__':
    main()
