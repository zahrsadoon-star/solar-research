"""Task 2: significance of the forecasting comparison.

(a) Friedman test across the 6 models per site, blocks = 45 folds (9 test months x 5 horizons), on per-fold Brier.
    RF/LightGBM per-fold Brier = mean over seeds 0..9 (seed-42 values used as a check). Post-hoc: Nemenyi
    (scikit-posthocs) and pairwise Wilcoxon signed-rank with Holm correction. Also Friedman per horizon (9 blocks).
    Caveat: the 5 horizons of one month share test hours, so the 45 blocks are not independent; the per-horizon
    tests (9 blocks, independent months) are the conservative version.
(b) Diebold-Mariano on hourly squared-error (Brier) loss, d_t = L_RF - L_HourMarkov (also RF - Logistic), over
    the contiguous out-of-sample Apr-Dec series, Newey-West/Bartlett HAC variance with lag h-1 (as specified),
    plus lags 24 and 168 because hourly outage losses are autocorrelated far beyond h-1. HLN small-sample
    correction is applied for lag h-1. RF = pilot seed 42; the spread over seeds 0..9 is reported too.
"""
from __future__ import annotations

import itertools

import matplotlib
import numpy as np
import pandas as pd
import scikit_posthocs as sp
from scipy import stats
from statsmodels.stats.multitest import multipletests

from common import CACHE, HERE, SITES

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

MODELS = ["Persistence", "Climatology", "HourMarkov", "Logistic", "LightGBM", "RandomForest"]


def fold_matrix(folds: pd.DataFrame, site: str, use_seed42: bool, h: int | None = None) -> pd.DataFrame:
    f = folds[folds.site == site]
    if h is not None:
        f = f[f.h == h]
    det = f[f.seed == -1]
    sto = f[f.seed == 42] if use_seed42 else f[(f.seed >= 0) & (f.seed != 42)]
    sto = sto.groupby(["h", "month", "model"]).brier.mean().reset_index()
    m = pd.concat([det[["h", "month", "model", "brier"]], sto]).pivot_table(
        index=["h", "month"], columns="model", values="brier")
    return m[MODELS]


def friedman_block(m: pd.DataFrame) -> dict:
    chi2, p = stats.friedmanchisquare(*[m[c].values for c in m.columns])
    n, k = m.shape
    ff = (n - 1) * chi2 / (n * (k - 1) - chi2)          # Iman-Davenport
    p_ff = stats.f.sf(ff, k - 1, (k - 1) * (n - 1))
    ranks = m.rank(axis=1).mean()
    cd = 2.850 * np.sqrt(k * (k + 1) / (6 * n))          # Nemenyi CD, alpha=0.05, k=6 (q=2.850)
    return {"n_blocks": n, "chi2": chi2, "p_friedman": p, "iman_davenport_F": ff, "p_iman_davenport": p_ff,
            "nemenyi_CD": cd, **{f"rank_{c}": ranks[c] for c in m.columns}}


def pairwise(m: pd.DataFrame, site: str, label: str) -> pd.DataFrame:
    nem = sp.posthoc_nemenyi_friedman(m.values)
    nem.index = nem.columns = m.columns
    rows = []
    for a, b in itertools.combinations(m.columns, 2):
        diff = m[a] - m[b]
        w = stats.wilcoxon(m[a], m[b], zero_method="wilcox")
        rows.append({"site": site, "blocks": label, "model_a": a, "model_b": b,
                     "median_brier_diff_a_minus_b": diff.median(), "a_better_in": int((diff < 0).sum()),
                     "n": len(diff), "wilcoxon_p": w.pvalue, "nemenyi_p": nem.loc[a, b]})
    r = pd.DataFrame(rows)
    r["wilcoxon_p_holm"] = multipletests(r.wilcoxon_p, method="holm")[1]
    return r


def dm_test(d: np.ndarray, lag: int, h: int, hln: bool) -> dict:
    """DM statistic with Newey-West (Bartlett) long-run variance of the loss differential d."""
    T = len(d)
    dc = d - d.mean()
    lrv = dc @ dc / T
    for j in range(1, lag + 1):
        lrv += 2 * (1 - j / (lag + 1)) * (dc[j:] @ dc[:-j]) / T
    dm = d.mean() / np.sqrt(lrv / T)
    if hln:   # Harvey, Leybourne & Newbold (1997)
        dm *= np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
        p = 2 * stats.t.sf(abs(dm), T - 1)
    else:
        p = 2 * stats.norm.sf(abs(dm))
    return {"T": T, "mean_loss_diff": d.mean(), "DM": dm, "p": p}


def diebold_mariano(hourly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    hourly = hourly.assign(loss=(hourly.p - hourly.y) ** 2)
    for site, h, (a, b) in itertools.product(SITES, [1, 3, 6, 12, 24],
                                             [("RandomForest", "HourMarkov"), ("RandomForest", "Logistic"),
                                              ("RandomForest", "Climatology")]):
        for seed, g in hourly[(hourly.site == site) & (hourly.h == h)].groupby("seed"):
            la = g[g.model == a].set_index("t").loss
            ref = hourly[(hourly.site == site) & (hourly.h == h) & (hourly.model == b) & (hourly.seed == 42)]
            lb = ref.set_index("t").loss
            if la.empty or lb.empty:
                continue
            assert la.index.equals(lb.index)
            assert (np.diff(la.index.values).astype("timedelta64[h]").astype(int) == 1).all()  # contiguous
            d = (la - lb).values
            for lag, hln in [(max(h - 1, 0), True), (24, False), (168, False)]:
                rows.append({"site": site, "h": h, "model_a": a, "model_b": b, "rf_seed": seed,
                             "hac_lag": lag, "hln": hln, **dm_test(d, lag, h, hln)})
    return pd.DataFrame(rows)


def main() -> None:
    folds = pd.read_csv(HERE / "seed_fold_scores.csv")
    fr, pw = [], []
    for site in SITES:
        for use42 in (False, True):
            m = fold_matrix(folds, site, use42)
            fr.append({"site": site, "horizons": "all (45 blocks)", "rf_lgbm": "seed42" if use42 else "mean seeds 0-9",
                       **friedman_block(m)})
            if not use42:
                pw.append(pairwise(m, site, "all"))
        for h in [1, 3, 6, 12, 24]:
            m = fold_matrix(folds, site, False, h)
            fr.append({"site": site, "horizons": f"h={h} (9 blocks)", "rf_lgbm": "mean seeds 0-9", **friedman_block(m)})
            pw.append(pairwise(m, site, f"h={h}"))
    fr = pd.DataFrame(fr)
    pw = pd.concat(pw)
    # Holm within each (site, blocks) family of 15 comparisons (pairwise() did that); also Nemenyi as given
    fr.to_csv(HERE / "friedman.csv", index=False)
    pw.to_csv(HERE / "posthoc_pairwise.csv", index=False)
    print(fr.round(4).to_string(index=False))
    print(pw[pw.blocks == "all"].round(4).to_string(index=False))

    # mean-rank plot with Nemenyi CD
    fig, axes = plt.subplots(1, 2, figsize=(11, 3))
    for ax, site in zip(axes, SITES):
        r = fr[(fr.site == site) & (fr.horizons.str.startswith("all")) & (fr.rf_lgbm != "seed42")].iloc[0]
        ranks = pd.Series({c: r[f"rank_{c}"] for c in MODELS}).sort_values()
        ax.scatter(ranks.values, range(len(ranks)), color="k")
        ax.set_yticks(range(len(ranks)), ranks.index)
        ax.errorbar(ranks.values, range(len(ranks)), xerr=r.nemenyi_CD / 2, fmt="none", ecolor="#2166ac", capsize=3)
        ax.set_xlabel("mean rank of per-fold Brier (1 = best); bars = Nemenyi CD/2")
        ax.set_title(f"{site}: Friedman p = {r.p_friedman:.1e}, CD = {r.nemenyi_CD:.2f} (45 blocks)")
    plt.tight_layout(); plt.savefig(HERE / "friedman_ranks.png", dpi=150); plt.close()

    hourly = pd.concat([pd.read_pickle(CACHE / f"hourly_seed{s}.pkl") for s in [42, *range(10)]])
    dm = diebold_mariano(hourly)
    dm.to_csv(HERE / "diebold_mariano_all.csv", index=False)
    key = dm[dm.model_b == "HourMarkov"]
    s42 = key[key.rf_seed == 42]
    spread = (key[key.rf_seed != 42].groupby(["site", "h", "hac_lag"]).agg(
        DM_min=("DM", "min"), DM_max=("DM", "max"), p_max=("p", "max")).reset_index())
    tab = s42.merge(spread, on=["site", "h", "hac_lag"])
    tab = pd.concat([tab, dm[(dm.model_b != "HourMarkov") & (dm.rf_seed == 42)]])
    tab.to_csv(HERE / "diebold_mariano.csv", index=False)
    print(tab[tab.h.isin([1, 6])].round(5).to_string(index=False))


if __name__ == "__main__":
    main()
