"""Check: does the coarse theta grid (0.05..0.95, pareto.py) bias the frontier comparison? HourMarkov and
Climatology risks take few distinct values, so their frontiers have few points and the LPSP at Mode 0's
high-SOC hours is read off long interpolation chords. Here every forecaster's theta grid is replaced by 99
quantiles of its own risk series (plus the original grid), base case 8 kWp, 10.2 kWh, H = 6 h.
Output: theta_grid_check.csv"""
import numpy as np
import pandas as pd

from bootstrap import frontier_stat, pv_unit, site_inputs
from common import HERE, PARETO_CAP_KWH, PARETO_THETAS, PILOT, SITES

FCS = ["RandomForest", "Logistic", "HourMarkov", "Climatology"]


def main() -> None:
    pvu, rows = pv_unit(), []
    for site in SITES:
        fc = pd.read_pickle(PILOT / "results" / f"forecasts_{site.lower()}_h6.pkl")
        inp = site_inputs(site, 6, {f: fc[f] for f in FCS}, pvu=pvu)
        for f in FCS:
            r = inp["risks"][f]
            fine = np.unique(np.r_[PARETO_THETAS, np.nanquantile(r, np.linspace(0.01, 0.99, 99)) - 1e-9])
            coarse = frontier_stat(inp["load"], inp["grid_on"], inp["pv"], inp["risks"], PARETO_CAP_KWH, [f])
            fin = frontier_stat(inp["load"], inp["grid_on"], inp["pv"], inp["risks"], PARETO_CAP_KWH, [f], fine)
            rows.append({"site": site, "forecast": f, "n_distinct_risk_values": len(np.unique(np.round(r[~np.isnan(r)], 6))), "n_nan_risk": int(np.isnan(r).sum()),
                         "LPSP_at_Mode0_high_soc_coarse_grid": coarse[f], "LPSP_at_Mode0_high_soc_fine_grid": fin[f],
                         "n_thetas_fine": len(fine), "Mode0_LPSP": coarse["Mode0_LPSP"]})
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(HERE / "theta_grid_check.csv", index=False)


if __name__ == "__main__":
    main()
