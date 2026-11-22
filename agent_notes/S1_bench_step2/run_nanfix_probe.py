"""Bound the prescribed full-grid probe to 180 seconds and retain only its log."""
from pathlib import Path
import json
import ctypes
from ctypes import wintypes
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = (ROOT / 'agent_notes/S1_bench_step2/nanfix_probe').resolve()
assert OUT.is_relative_to(ROOT / 'agent_notes/S1_bench_step2')
OUT.mkdir(exist_ok=True)
if list(OUT.iterdir()):
    raise RuntimeError('Probe requires empty scratch directory')
command = [sys.executable, '-u', 'studies/S1_outage_forecasting/benchmark/tuning.py',
           '--sites', 'BG', 'KR', '--horizons', '1', '6', '--K', '8', '--n-jobs', '4', '--out', str(OUT)]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
           MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel.CreateJobObjectW.restype = wintypes.HANDLE
kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
job = kernel.CreateJobObjectW(None, None)
if not job:
    raise ctypes.WinError(ctypes.get_last_error())
started = time.perf_counter()
with (OUT / 'stdout.txt').open('w') as stdout, (OUT / 'stderr.txt').open('w') as stderr:
    process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, env=env)
    if not kernel.AssignProcessToJobObject(job, int(process._handle)):
        process.kill()
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        code = process.wait(timeout=max(0, 180 - (time.perf_counter() - started)))
        termination = f'Exited early: {code}'
    except subprocess.TimeoutExpired:
        if not kernel.TerminateJobObject(job, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        process.wait(timeout=10)
        termination = "TerminateJobObject succeeded: parent and all inherited worker processes stopped"
    finally:
        kernel.CloseHandle(job)
elapsed = time.perf_counter() - started
sys.path.insert(0, str(ROOT / 'studies/S1_outage_forecasting/benchmark'))
import tuning
paths = list((OUT / 'checkpoints').glob('*.json'))
complete = 0
failed = 0
for path in paths:
    value = json.loads(path.read_text(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    if 'payload' not in value:
        continue
    unit = value['payload']
    if unit['status'] == 'complete':
        tuning.read_checkpoint(path, unit['identity'], unit['manifest'], unit['rows'], unit['identity']['algorithm'])
        complete += 1
    else:
        failed += 1
log = {'command': command, 'elapsed_seconds': elapsed, 'exit_code_after_stop': process.returncode,
       'termination': termination, 'json_files_validated': len(paths), 'complete_units_validated': complete,
       'failed_units': failed, 'stdout': (OUT / 'stdout.txt').read_text(), 'stderr': (OUT / 'stderr.txt').read_text(),
       'scope': '180-second probe only; no full-grid completion claim'}
for child in OUT.iterdir():
    assert child.resolve().is_relative_to(OUT)
    if child.is_dir():
        shutil.rmtree(child)
    else:
        child.unlink()
(OUT / 'probe.log').write_text(json.dumps(log, indent=2, allow_nan=False))
print(json.dumps(log, indent=2, allow_nan=False))
