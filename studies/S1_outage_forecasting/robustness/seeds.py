"""Task 1: seed robustness of the forecasting benchmark (pilot_s1.evaluate_site, temp=False, both sites).

- seed 42 run with all models = exact rerun of the pilot (check against pilot/results/fold_scores.csv);
  deterministic models (Persistence, Climatology, HourMarkov, Logistic) are taken from this run.
- seeds 0..9: RandomForest and LightGBM only (pilot_s1.SEED / ml_models monkeypatched, evaluate_site reused).
Outputs: cache/fold_seed*.pkl, cache/hourly_seed*.pkl, seed_fold_scores.csv, seed_skill_summary.csv
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from common import CACHE, HERE, PILOT, SITES, test_index
import pilot_s1 as P

SEEDS = list(range(10))
_orig_ml_models = P.ml_models


def run_seed(seed: int, stochastic_only: bool) -> None:
    f_fold, f_hour = CACHE / f"fold_seed{seed}.pkl", CACHE / f"hourly_seed{seed}.pkl"
    if f_fold.exists() and f_hour.exists():
        return
    P.SEED = seed
    if stochastic_only:
        P.ml_models = lambda: {k: v for k, v in _orig_ml_models().items() if k in ("RandomForest", "LightGBM")}
    else:
        P.ml_models = _orig_ml_models
    sites = P.load_sites()
    folds, hourly = [], []
    for s in SITES:
        t0 = time.time()
        rows, preds = P.evaluate_site(s, sites[s], with_temp=False)
        # attach issue times: preds are concatenated h -> month -> model, each block in time order
        idx = {h: test_index(sites[s], h) for h in P.HORIZONS}
        parts = []
        for (h, mdl), g in preds.groupby(["h", "model"], sort=False):
            t = np.concatenate([idx[h][m].values for m in sorted(idx[h])])
            assert len(t) == len(g), (s, h, mdl)
            parts.append(g.assign(t=t))
        hp = pd.concat(parts)
        if stochastic_only:
            hp = hp[hp.model.isin(["RandomForest", "LightGBM"])]
            rows = [r for r in rows if r["model"] in ("RandomForest", "LightGBM")]
        folds.append(pd.DataFrame(rows).assign(seed=seed))
        hourly.append(hp.assign(seed=seed))
        print(f"seed {seed} {s}: {time.time() - t0:.0f} s", flush=True)
    pd.concat(folds).to_pickle(f_fold)
    pd.concat(hourly).to_pickle(f_hour)
    P.ml_models = _orig_ml_models


def skill_table(folds: pd.DataFrame) -> pd.DataFrame:
    """Brier skill vs climatology, defined as in pilot_s1.main: 1 - mean_fold(Brier) / mean_fold(Brier_clim)."""
    clim = folds[folds.model == "Climatology"].groupby(["site", "h"]).brier.mean().rename("brier_clim")
    g = folds.groupby(["site", "h", "model", "seed"]).brier.mean().reset_index().join(clim, on=["site", "h"])
    g["skill"] = 1 - g.brier / g.brier_clim
    return g


def main() -> None:
    run_seed(42, stochastic_only=False)
    for s in SEEDS:
        run_seed(s, stochastic_only=True)
    base = pd.read_pickle(CACHE / "fold_seed42.pkl")
    # reproduction check against the pilot
    pil = pd.read_csv(PILOT / "results" / "fold_scores.csv")
    pil = pil[~pil.temp]
    chk = base.merge(pil, on=["site", "h", "month", "model"], suffixes=("", "_pilot"))
    max_dev = float((chk.brier - chk.brier_pilot).abs().max())
    print(f"seed-42 rerun vs pilot fold_scores.csv: {len(chk)} rows, max |dBrier| = {max_dev:.2e}")
    det = base[~base.model.isin(["RandomForest", "LightGBM"])].assign(seed=-1)   # deterministic
    sto = pd.concat([pd.read_pickle(CACHE / f"fold_seed{s}.pkl") for s in SEEDS])
    folds = pd.concat([det, sto, base[base.model.isin(["RandomForest", "LightGBM"])].assign(seed=42)])
    folds.to_csv(HERE / "seed_fold_scores.csv", index=False)
    ten = folds[folds.seed != 42]                                       # deterministic + seeds 0..9
    sk = skill_table(ten)
    summ = (sk.groupby(["site", "h", "model"]).skill.agg(skill_mean="mean", skill_sd="std", skill_min="min",
                                                         skill_max="max", n_seeds="count").reset_index())
    pilot42 = skill_table(base.assign(seed=42)).set_index(["site", "h", "model"]).skill.rename("skill_pilot_seed42")
    summ = summ.join(pilot42, on=["site", "h", "model"])
    # does RF beat HourMarkov and Climatology in every fold (h=1..6), per seed?  (REPORT: "27 of 27")
    piv = ten.pivot_table(index=["site", "h", "month", "seed"], columns="model", values="brier").reset_index()
    detp = piv[piv.seed == -1].drop(columns=["seed", "RandomForest", "LightGBM"], errors="ignore")
    rfp = piv[piv.seed >= 0][["site", "h", "month", "seed", "RandomForest", "LightGBM"]]
    w = rfp.merge(detp, on=["site", "h", "month"])
    w = w[w.h <= 6]
    w["rf_beats_both"] = (w.RandomForest < w.HourMarkov) & (w.RandomForest < w.Climatology)
    wins = w.groupby(["site", "seed"]).rf_beats_both.agg(["sum", "count"]).reset_index()
    wins.to_csv(HERE / "seed_rf_wins_h1to6.csv", index=False)
    summ.to_csv(HERE / "seed_skill_summary.csv", index=False)
    pd.DataFrame([{"rows_compared": len(chk), "max_abs_brier_dev": max_dev}]).to_csv(
        HERE / "seed42_reproduction_check.csv", index=False)
    print(summ.round(3).to_string(index=False))
    print(wins.groupby("site")[["sum", "count"]].agg(["min", "max"]))


if __name__ == "__main__":
    main()
