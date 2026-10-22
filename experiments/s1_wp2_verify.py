"""Verify persisted smoke artifacts independently of fitting and selection."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from eval.artifacts import cache_key, read_predictions, select
from eval.config import CONFIG_PATH, load_config
from eval.metrics import brier, choose_threshold
from outage.data import RAW, ANALYSIS, WEATHER

ROOT = Path(__file__).resolve().parents[1]

def verify() -> dict:
    """Check hashes, probability bounds, pairing, selections and pooled scores."""
    output = ROOT/'results/S1/wp2_smoke'; c = load_config()
    inputs = [CONFIG_PATH,output/'config/effective.yaml',*sorted((ROOT/'src/eval').glob('*.py')),RAW/ANALYSIS,RAW/WEATHER]
    if (ROOT/c.calendar_path).exists(): inputs.append(ROOT/c.calendar_path)
    key = cache_key(inputs)
    assert key == json.loads((output/'config/run.json').read_text())['cache_key']
    paths = list((output/'predictions').glob('*.parquet'))
    expected = (len(c.models)+2*(len(c.window_days)-1))*len(c.horizons)*(c.last_test_month-c.first_test_month+1)*len(c.evaluation_seeds)
    assert len(paths) == expected
    for path in paths:
        test = read_predictions(path,key); inner = read_predictions(output/'predictions/innerval'/path.name,key)
        assert len(test) and len(inner)
        assert test.p.between(0,1).all() and inner.p.between(0,1).all()
        assert np.isfinite(test.p).all() and np.isfinite(inner.p).all()
        assert (test.origin-test.row_time == pd.Timedelta(hours=c.issuance_offset_h)).all()
        assert inner.origin.max() < test.origin.min()
        assert test.threshold.eq(choose_threshold(inner.y.to_numpy(),inner.p.to_numpy())).all()
    selections = pd.read_csv(output/'metrics/selection.csv')
    for row in selections.itertuples():
        tags = [row.trailing if m=='trailing' else row.recency if m=='recency' else m for m in c.models]
        chosen,_ = select({tag:output/'predictions/innerval'/f'{tag}_a_h{row.horizon}_fold{row.fold}_seed{row.seed}.parquet' for tag in tags},output,key,c.selection_tolerance)
        assert chosen == row.strongest
    pooled = pd.read_csv(output/'metrics/pooled.csv'); folds = pd.read_csv(output/'metrics/folds.csv')
    for row in pooled.itertuples():
        group = folds[(folds.model == row.model)&(folds.horizon == row.horizon)]
        assert np.isclose(row.brier,np.average(group.brier,weights=group.n),rtol=0,atol=1e-14)
    result = {'verified':True,'test_prediction_files':len(paths),'inner_prediction_files':len(list((output/'predictions/innerval').glob('*.parquet'))),'pooled_metric_rows':len(pooled),'selection_rows':len(selections),'cache_key':key}
    (output/'tests/artifact_report.json').write_text(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    print(json.dumps(verify(),indent=2))
