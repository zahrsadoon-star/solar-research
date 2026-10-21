"""Regenerate every table/figure in robustness/ (S1 pilot robustness analysis).

Order: seeds.py (Task 1, ~22 min on 2 cores) -> stats_tests.py (Task 2) -> bootstrap.py (Task 3, ~12 min)
-> sensitivity.py (Task 4, ~20 min incl. new H=12 and RF-seed forecasts). Intermediate results are cached in
robustness/cache/; delete that folder to recompute from scratch.
Run:  /home/claude/venv/bin/python run_all.py
"""
import time

import bootstrap
import seeds
import sensitivity
import stats_tests

if __name__ == "__main__":
    for mod in (seeds, stats_tests, bootstrap, sensitivity):
        t0 = time.time()
        print(f"===== {mod.__name__}", flush=True)
        mod.main()
        print(f"===== {mod.__name__} done in {time.time() - t0:.0f} s", flush=True)
