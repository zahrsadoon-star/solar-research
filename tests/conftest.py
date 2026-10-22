"""Persist machine-generated WP2 leakage evidence, including expected failures."""
import json
import time
from pathlib import Path

_START = 0.0
_REPORTS = []

def pytest_sessionstart(session):
    global _START
    _START = time.perf_counter()
    _REPORTS.clear()

def pytest_runtest_logreport(report):
    if 'test_eval_' in report.nodeid and (report.when == 'call' or report.failed):
        _REPORTS.append({'test':report.nodeid,'outcome':report.outcome,'expected_failure':getattr(report,'wasxfail',None),'duration_seconds':report.duration})

def pytest_sessionfinish(session,exitstatus):
    root = Path(__file__).resolve().parents[1]/'results/S1/wp2_smoke/tests'
    root.mkdir(parents=True,exist_ok=True)
    (root/'leakage_report.json').write_text(json.dumps({'pytest_exit_status':int(exitstatus),'suite_elapsed_seconds':time.perf_counter()-_START,'scientific_gate_cleared':False,'reason':'Hour convention requires independent evidence; strict xfail remains.','tests':_REPORTS},indent=2))
