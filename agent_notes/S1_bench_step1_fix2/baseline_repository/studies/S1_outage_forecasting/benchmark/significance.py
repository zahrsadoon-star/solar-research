"""S1 benchmark, step 1: is the best algorithm really better, or is the top group a tie?

For each site (BG, KR) and horizon (1 h, 6 h): the six best algorithms of benchmark v1 (by Brier score) are re-run
with the identical time-ordered protocol of benchmark.py, keeping every hourly prediction. Then, against the
best-ranked algorithm of that case:
  - Diebold-Mariano test on the hourly Brier loss difference, with a Newey-West (HAC) variance, lag = 24 h,
    two-sided, Holm correction over the comparisons within each case;
  - moving-block bootstrap (block = 7 days = 168 h, 2,000 replicates) 95 % CI of the Brier difference and of the
    accuracy difference.
A difference is called real only if the CI excludes 0 AND Holm-adjusted p < 0.05.
Run:  python significance.py   -> results/significance.csv, results/hourly_predictions_top6.csv.gz
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import benchmark as bm

TOP = 6
B, BLOCK, LAG = 2000, 168, 24
rng = np.random.default_rng(42)


def hourly_predictions(site: str, h: int, names: list[str]) -> pd.DataFrame:
    d = bm.load(site)
    X, y = bm.features(d, h), d["outage"].shift(-h)
    ok = X.notna().all(axis=1) & y.notna()
    X, y = X[ok], y[ok].astype(int)
    t_target = X.index + pd.Timedelta(hours=h)
    out = []
    for m in range(4, 13):
        start = pd.Timestamp(f"2018-{m:02d}-01")
        tr = (X.index < start) & (t_target < start)
        te = X.index.month == m
        fold = pd.DataFrame({"time": X.index[te], "y": y[te].values})
        for name in names:
            mdl = bm.algorithms()[name]
            mdl.fit(X[tr], y[tr])
            fold[name] = mdl.predict_proba(X[te])[:, 1]
        out.append(fold)
    return pd.concat(out, ignore_index=True)


def dm_test(loss_diff: np.ndarray, lag: int = LAG) -> tuple[float, float]:
    """Diebold-Mariano statistic with Newey-West variance (Bartlett kernel)."""
    d = loss_diff - loss_diff.mean()
    n = len(d)
    gamma0 = np.dot(d, d) / n
    var = gamma0 + 2 * sum((1 - k / (lag + 1)) * np.dot(d[k:], d[:-k]) / n for k in range(1, lag + 1))
    dm = loss_diff.mean() / np.sqrt(var / n)
    return float(dm), float(2 * (1 - stats.norm.cdf(abs(dm))))


def block_bootstrap_ci(x: np.ndarray) -> tuple[float, float]:
    n = len(x)
    nblocks = int(np.ceil(n / BLOCK))
    starts = rng.integers(0, n - BLOCK + 1, size=(B, nblocks))
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(B, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def holm(p: list[float]) -> list[float]:
    order = np.argsort(p)
    adj, running = np.empty(len(p)), 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def main() -> None:
    res = pd.read_csv(bm.OUT / "benchmark_results.csv")
    rows, all_preds = [], []
    for (site, h), g in res[res.kind == "algorithm"].groupby(["site", "h"]):
        names = g.sort_values("brier").algorithm.head(TOP).tolist()
        pr = hourly_predictions(site, h, names)
        pr.insert(0, "h", h); pr.insert(0, "site", site)
        all_preds.append(pr)
        y = pr["y"].values
        best = names[0]
        loss_best = (pr[best].values - y) ** 2
        acc_best = ((pr[best].values >= 0.5) == y).astype(float)
        case = []
        for other in names[1:]:
            loss_o = (pr[other].values - y) ** 2
            acc_o = ((pr[other].values >= 0.5) == y).astype(float)
            diff = loss_o - loss_best                     # > 0 means `best` is better
            dm, p = dm_test(diff)
            lo, hi = block_bootstrap_ci(diff)
            alo, ahi = block_bootstrap_ci(acc_best - acc_o)
            case.append({"site": site, "h": h, "best": best, "other": other,
                         "brier_best": loss_best.mean(), "brier_other": loss_o.mean(),
                         "brier_diff": diff.mean(), "brier_diff_ci_low": lo, "brier_diff_ci_high": hi,
                         "acc_best_minus_other_pp": 100 * (acc_best - acc_o).mean(),
                         "acc_diff_ci_low_pp": 100 * alo, "acc_diff_ci_high_pp": 100 * ahi,
                         "dm_stat": dm, "p_value": p})
        for r, padj in zip(case, holm([r["p_value"] for r in case])):
            r["p_holm"] = padj
            r["best_really_better"] = bool(padj < 0.05 and r["brier_diff_ci_low"] > 0)
        rows += case
    out = pd.DataFrame(rows)
    out.round(5).to_csv(bm.OUT / "significance.csv", index=False)
    pd.concat(all_preds).round(5).to_csv(bm.OUT / "hourly_predictions_top6.csv.gz", index=False)
    pd.set_option("display.width", 220)
    print(out[["site", "h", "best", "other", "brier_diff", "brier_diff_ci_low", "brier_diff_ci_high",
               "acc_best_minus_other_pp", "p_holm", "best_really_better"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
