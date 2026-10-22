"""Probability and censored-duration metrics with explicit edge behavior."""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score, matthews_corrcoef, f1_score
from .config import Config, load_config

def brier(y: np.ndarray, p: np.ndarray) -> float:
    """Mean squared probability error (unitless)."""
    return float(np.mean((np.asarray(y)-np.asarray(p))**2))

def bss(y: np.ndarray, p: np.ndarray, reference: np.ndarray) -> float:
    """Ratio of pooled loss sums, never mean monthly skill."""
    denominator = np.sum((np.asarray(y)-reference)**2)
    return float(1-np.sum((np.asarray(y)-p)**2)/denominator) if denominator else np.nan

def log_loss(y: np.ndarray, p: np.ndarray, clip: float | None = None) -> float:
    """Clipping is used only for logarithmic loss."""
    eps = load_config().logloss_clip if clip is None else clip
    p = np.clip(p, eps, 1-eps); y = np.asarray(y)
    return float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p)))

def reliability(y: np.ndarray, p: np.ndarray, bins: int | None = None) -> pd.DataFrame:
    """Equal-width probability bins, including empty bins and p=1."""
    n = bins or load_config().ece_bins; y = np.asarray(y); p = np.asarray(p)
    assignments = np.minimum((p*n).astype(int), n-1)
    rows = []
    for k in range(n):
        use = assignments == k
        rows.append({'lower': k/n, 'upper': (k+1)/n, 'count': int(use.sum()), 'mean_prediction': float(p[use].mean()) if use.any() else np.nan, 'frequency': float(y[use].mean()) if use.any() else np.nan})
    return pd.DataFrame(rows)

def ece(y: np.ndarray, p: np.ndarray, bins: int | None = None) -> float:
    table = reliability(y, p, bins)
    return float((table['count']*(table.frequency-table.mean_prediction).abs()).sum()/len(y))

def choose_threshold(y: np.ndarray, p: np.ndarray) -> float:
    """Maximum MCC; ties use smallest threshold; includes all-negative rule."""
    candidates = np.r_[np.unique(p), np.nextafter(1., np.inf)]
    # Vectorized confusion counts avoid quadratic sklearn dispatch overhead.
    order = np.argsort(p); pp = np.asarray(p)[order]; yy = np.asarray(y)[order]
    prefix = np.r_[0, np.cumsum(yy)]; split = np.searchsorted(pp, candidates)
    tp = prefix[-1]-prefix[split]; fp = len(yy)-split-tp
    fn = prefix[split]; tn = split-fn
    den = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    scores = np.divide(tp*tn-fp*fn, den, out=np.zeros_like(den, dtype=float), where=den > 0)
    return float(candidates[np.argmax(scores)])

def classification(y: np.ndarray, p: np.ndarray, threshold: float, config: Config | None = None) -> dict:
    c = config or load_config(); binary = np.asarray(p) >= threshold
    both = len(np.unique(y)) == 2
    return {'brier': brier(y,p), 'log_loss': log_loss(y,p,c.logloss_clip), 'roc_auc': float(roc_auc_score(y,p)) if both else np.nan, 'pr_auc': float(average_precision_score(y,p)) if both else np.nan, 'mcc': float(matthews_corrcoef(y,binary)), 'f1': float(f1_score(y,binary,zero_division=0)), 'ece': ece(y,p,c.ece_bins)}

def duration_mae(duration: np.ndarray, prediction: np.ndarray, event: np.ndarray) -> float:
    """MAE in hours, restricted to observed restorations."""
    use = np.asarray(event, dtype=bool) & np.isfinite(duration)
    return float(np.mean(np.abs(np.asarray(duration)[use]-np.asarray(prediction)[use]))) if use.any() else np.nan

def harrell_c(duration: np.ndarray, prediction: np.ndarray, event: np.ndarray) -> float:
    """Concordance for predicted duration (larger means later restoration)."""
    d,p,e = map(np.asarray, (duration,prediction,event)); score = count = 0
    for i in range(len(d)):
        if not e[i] or not np.isfinite(d[i]): continue
        use = (d > d[i]) & np.isfinite(p) & np.isfinite(p[i])
        count += use.sum(); score += (p[use] > p[i]).sum()+.5*(p[use] == p[i]).sum()
    return float(score/count) if count else np.nan
