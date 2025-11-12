"""
Minimal synchronous task helper for imports.

This module intentionally avoids Celery. It provides a single
function `import_file_task(upload_path, periodo=None)` that runs the
management command `import_estudiantes` and writes a small status JSON
next to the uploaded file so the UI can show progress.
"""

import os
import json
import traceback
from django.core.management import call_command
from datetime import datetime


def _status_path_for(upload_path):
    return f"{upload_path}.status.json"


def _write_status(upload_path, data):
    sp = _status_path_for(upload_path)
    try:
        with open(sp, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _run_import_and_track(upload_path, periodo=None):
    status = {
        'status': 'processing',
        'started_at': datetime.now().isoformat(),
        'periodo': periodo,
        'message': ''
    }
    _write_status(upload_path, status)
    try:
        if periodo:
            call_command('import_estudiantes', upload_path, periodo=periodo)
        else:
            call_command('import_estudiantes', upload_path)
        # If the import command wrote a status file with extra fields (errors_log, processed, total),
        # merge them instead of overwriting.
        sp = _status_path_for(upload_path)
        final = {'status': 'done', 'finished_at': datetime.now().isoformat()}
        try:
            if os.path.exists(sp):
                with open(sp, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                # merge while favoring existing values for keys like errors_log, processed, total
                existing.update(final)
                _write_status(upload_path, existing)
            else:
                _write_status(upload_path, final)
        except Exception:
            _write_status(upload_path, final)
    except Exception as e:
        tb = traceback.format_exc()
        # Merge failure info with any existing status file so we don't lose errors_log or progress
        sp = _status_path_for(upload_path)
        fail = {
            'status': 'failed',
            'finished_at': datetime.now().isoformat(),
            'message': str(e),
            'traceback': tb,
        }
        try:
            if os.path.exists(sp):
                with open(sp, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                existing.update(fail)
                _write_status(upload_path, existing)
            else:
                _write_status(upload_path, fail)
        except Exception:
            _write_status(upload_path, fail)


def import_file_task(upload_path, periodo=None):
    """Run import synchronously and track status.

    Kept as a simple function so `from . import tasks` continues to work
    and views can call `tasks.import_file_task(...)` without Celery.
    """
    _run_import_and_track(upload_path, periodo=periodo)
