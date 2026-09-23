"""Launches training.retrain as a background subprocess and tracks its status.
Shared by routes/api.py (token-protected, for the papi backend) and routes/web.py
(the UI button) so both go through the same lock/state -- avoids two independent
copies of the anti-double-launch guard racing each other.

NB: this module-level state only protects concurrency under gunicorn --workers 1
(current Dockerfile config). Moving to several workers silently breaks the
anti-double-launch guard (each worker would have its own copy of these variables).
"""
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone

HISTORY_PATH = os.path.join('models', 'history.json')
RETRAIN_LOG_DIR = 'logs'

_retrain_lock = threading.Lock()
sync_lock = threading.Lock()
_retrain_process = None       # Popen of the last run started
_retrain_started_at = None
_retrain_log_path = None


def is_running():
    # poll() is non-blocking and also reaps the process once it's done.
    return _retrain_process is not None and _retrain_process.poll() is None


def start(cwd, no_prepare=False, no_sync=False, force=False, tolerance=None):
    """Returns (payload_dict, http_status)."""
    global _retrain_process, _retrain_started_at, _retrain_log_path

    cmd = [sys.executable, '-m', 'training.retrain']
    if no_prepare:
        cmd.append('--no-prepare')
    if no_sync:
        cmd.append('--no-sync')
    if force:
        cmd.append('--force')
    if tolerance is not None:
        cmd += ['--tolerance', str(tolerance)]

    with _retrain_lock:
        if is_running():
            return {'error': 'retrain déjà en cours', 'started_at': _retrain_started_at,
                    'pid': _retrain_process.pid}, 409
        if not no_sync and sync_lock.locked():
            return {'error': 'synchro papi en cours : réessayer ou passer no_sync=true'}, 409

        os.makedirs(RETRAIN_LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = os.path.join(RETRAIN_LOG_DIR, f'retrain_{ts}.log')
        with open(log_path, 'wb') as log_file:
            _retrain_process = subprocess.Popen(cmd, cwd=cwd, stdout=log_file, stderr=subprocess.STDOUT)
        _retrain_started_at = datetime.now(timezone.utc).isoformat()
        _retrain_log_path = log_path

    return {'status': 'started', 'pid': _retrain_process.pid,
            'started_at': _retrain_started_at, 'log': log_path}, 202


def status():
    running = is_running()
    history = []
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, encoding='utf-8') as f:
            history = json.load(f)

    response = {'running': running, 'last_run': history[-1] if history else None}
    if _retrain_process is not None:
        response['pid'] = _retrain_process.pid
        response['started_at'] = _retrain_started_at
        response['log'] = _retrain_log_path
        if not running:
            response['returncode'] = _retrain_process.returncode
    return response
