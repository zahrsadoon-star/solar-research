"""Artifact scope enforcement and content-addressed prediction files."""
import hashlib
from pathlib import Path
import pandas as pd
from .metrics import brier, choose_threshold

def cache_key(paths: list[Path]) -> str:
    """Hash YAML, feature/evaluation code, and source data bytes, in order."""
    digest = hashlib.sha256()
    for path in paths:
        payload = Path(path).read_bytes(); digest.update(len(payload).to_bytes(8,'big')); digest.update(payload)
    return digest.hexdigest()

def write_predictions(path: Path, frame: pd.DataFrame, key: str) -> None:
    """Persist predictions with a content-key sidecar."""
    path.parent.mkdir(parents=True,exist_ok=True)
    frame.to_parquet(path,index=False); path.with_suffix('.sha256').write_text(key)

def read_predictions(path: Path, key: str) -> pd.DataFrame:
    """Reject incompatible artifacts before reading their data."""
    if path.with_suffix('.sha256').read_text() != key: raise ValueError('Cache key mismatch')
    return pd.read_parquet(path)

def read_innerval(path: Path, root: Path, key: str) -> pd.DataFrame:
    """Selection inputs must reside inside predictions/innerval/."""
    path.resolve().relative_to((root/'predictions'/'innerval').resolve())
    return read_predictions(path,key)

def select(paths: dict[str,Path], root: Path, key: str, tolerance: float) -> tuple[str,dict]:
    """Seed-mean Brier, ordered tolerance ties; saved validation inputs only."""
    scores = {}
    for name,path in paths.items():
        frame = read_innerval(path,root,key)
        scores[name] = float(frame.assign(loss=(frame.y-frame.p)**2).groupby('seed').loss.mean().mean())
    best = next(iter(scores))
    for name,score in scores.items():
        if score < scores[best]-tolerance: best = name
    return best,scores

def threshold(path: Path, root: Path, key: str) -> float:
    frame = read_innerval(path,root,key)
    return choose_threshold(frame.y.to_numpy(),frame.p.to_numpy())
