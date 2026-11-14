"""Exercise heavy-job arbitration across processes using a disposable SQLite file."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest


BOOTSTRAP = r'''
import os
import django
django.setup()
from django.db import connection
from home.models import GovernorLock, HeavyJob
connection.settings_dict['NAME'] = os.environ['GOV_TEST_DB']
with connection.schema_editor() as schema:
    schema.create_model(GovernorLock)
    schema.create_model(HeavyJob)
'''

WORKER = r'''
import json, os, time
from pathlib import Path
import django
django.setup()
from django.db import connection
from home.heavy_job_governor import HeavyJobGovernor
connection.settings_dict['NAME'] = os.environ['GOV_TEST_DB']
root = Path(os.environ['GOV_TEST_ROOT'])
name = os.environ['GOV_TEST_WORKER']
(root / (name + '.ready')).touch()
deadline = time.monotonic() + 20
while not (root / 'start').exists():
    if time.monotonic() >= deadline:
        raise RuntimeError('start barrier timed out')
    time.sleep(0.01)
governor = HeavyJobGovernor(queue_capacity=2, wait_timeout=10, acquire_interval=0.05)
with governor.slot('local_inference', name, name):
    entered = time.monotonic_ns()
    time.sleep(0.4)
    leaving = time.monotonic_ns()
(root / (name + '.json')).write_text(json.dumps([entered, leaving]))
'''


class HeavyGovernorMultiprocessTests(unittest.TestCase):
    def test_two_processes_never_hold_the_seat_together(self):
        with tempfile.TemporaryDirectory(prefix='governor-process-') as directory:
            root = Path(directory)
            environment = os.environ.copy()
            environment.update({
                'DJANGO_SETTINGS_MODULE': 'superharry.settings',
                'GOV_TEST_DB': str(root / 'isolated.sqlite3'),
                'GOV_TEST_ROOT': directory,
            })
            subprocess.run([sys.executable, '-c', BOOTSTRAP], env=environment,
                           check=True, capture_output=True, text=True, timeout=30)
            processes = []
            try:
                for name in ('first', 'second'):
                    worker_env = environment | {'GOV_TEST_WORKER': name}
                    processes.append(subprocess.Popen(
                        [sys.executable, '-c', WORKER], env=worker_env,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    ))
                deadline = time.monotonic() + 30
                while not all((root / (name + '.ready')).exists() for name in ('first', 'second')):
                    self.assertLess(time.monotonic(), deadline, 'worker startup timed out')
                    self.assertTrue(all(process.poll() is None for process in processes), 'worker exited before startup')
                    time.sleep(0.02)
                (root / 'start').touch()
                for process in processes:
                    stdout, stderr = process.communicate(timeout=30)
                    self.assertEqual(process.returncode, 0, f'{stdout}\n{stderr}')
                intervals = sorted(json.loads((root / (name + '.json')).read_text())
                                   for name in ('first', 'second'))
                self.assertLessEqual(intervals[0][1], intervals[1][0], intervals)
                with closing(sqlite3.connect(root / 'isolated.sqlite3')) as database:
                    self.assertEqual(database.execute('SELECT count(*) FROM home_governor_lock').fetchone()[0], 1)
                    self.assertEqual(
                        database.execute('SELECT state, count(*) FROM home_heavyjob GROUP BY state').fetchall(),
                        [('released', 2)],
                    )
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()
