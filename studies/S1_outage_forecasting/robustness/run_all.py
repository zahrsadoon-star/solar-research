"""Regenerate every table/figure in robustness/ (S1 pilot robustness analysis).

Order: seeds.py (Task 1, ~22 min on 2 cores) -> stats_tests.py (Task 2) -> bootstrap.py (Task 3, ~35 min)
-> sensitivity.py (Task 4, ~26 min incl. new H=12 and RF-seed forecasts) -> theta_grid_check.py (~2 min).
Total from scratch ~95 min on 2 cores. Intermediate results are cached in
robustness/cache/; delete that folder to recompute from scratch.
Run:  /home/claude/venv/bin/python run_all.py
"""
import time

import bootstrap
import seeds
import sensitivity
import stats_tests
import theta_grid_check

if __name__ == "__main__":
    for mod in (seeds, stats_tests, bootstrap, sensitivity, theta_grid_check):
        t0 = time.time()
        print(f"===== {mod.__name__}", flush=True)
        mod.main()
        print(f"===== {mod.__name__} done in {time.time() - t0:.0f} s", flush=True)
