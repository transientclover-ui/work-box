import json
import os
from pathlib import Path
import signal
import sys
import time
import pytest
from workbox.storage import Box
from workbox.runner import Run


class FakeAdapter:
    id = 'fake'
    def __init__(self, script):
        self.script = script
    def launch_args(self, executable, cwd):
        return [sys.executable, '-u', '-c', self.script]


def wait_for(predicate, timeout=8):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(.03)
    raise AssertionError('Timed out')


def test_success_persists_context_and_log(tmp_path):
    b = Box.create(tmp_path, 'Box')
    run = Run(b, FakeAdapter('import sys; print(sys.stdin.read()); print("result")'), '', tmp_path, 'do work')
    wait_for(lambda: not run.active)
    assert run.state()['status'] == 'completed'
    assert 'do work' in (run.directory / 'worker.log').read_text()
    assert (run.directory / 'context.json').is_file()
    run.process.stdin.close(); b.close()


def test_nonzero_and_missing_executable(tmp_path):
    b = Box.create(tmp_path, 'Box')
    run = Run(b, FakeAdapter('raise SystemExit(7)'), '', tmp_path, 'fail')
    wait_for(lambda: not run.active)
    assert run.state()['status'] == 'failed'
    assert run.state()['exit_code'] == 7
    run.process.stdin.close(); b.close()


def test_halt_kills_stubborn_process_group_preserves_results(tmp_path):
    b = Box.create(tmp_path, 'Box')
    script = '''import os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(100)'])
open('child.pid','w').write(str(child.pid))
open('result.txt','w').write('safe')
time.sleep(100)
'''
    run = Run(b, FakeAdapter(script), '', tmp_path, 'work')
    try:
        wait_for(lambda: (tmp_path / 'result.txt').exists())
        run.halt(); run.halt()
        wait_for(lambda: not run.active)
        assert run.state()['status'] == 'interrupted'
        assert run.state()['halt_requested']
        assert (tmp_path / 'result.txt').read_text() == 'safe'
        pid = int((tmp_path / 'child.pid').read_text())
        proc = Path(f'/proc/{pid}/stat')
        assert not proc.exists() or proc.read_text().split()[2] == 'Z'
    finally:
        run.halt(); run.process.wait(timeout=8); b.close()


def test_parent_disconnect_stops_worker_and_lock_survives_parent(tmp_path):
    b = Box.create(tmp_path, 'Box')
    run = Run(b, FakeAdapter('import time; time.sleep(100)'), '', tmp_path, 'work')
    wait_for(lambda: run.state()['status'] == 'running')
    b.close()
    with pytest.raises(ValueError, match='already open'):
        Box(tmp_path)
    run.process.stdin.close()  # Equivalent to a GUI crash closing its pipe.
    wait_for(lambda: not run.active)
    assert run.state()['status'] == 'interrupted'
    Box(tmp_path).close()


def test_immediate_halt(tmp_path):
    b = Box.create(tmp_path, 'Box')
    run = Run(b, FakeAdapter('import time; time.sleep(100)'), '', tmp_path, 'work')
    run.halt()
    wait_for(lambda: not run.active)
    assert run.state()['status'] == 'interrupted'
    b.close()


def test_launch_missing_program_records_failure(tmp_path):
    class MissingAdapter:
        id = 'fake'
        def launch_args(self, executable, cwd):
            return [str(tmp_path / 'not-installed')]
    b = Box.create(tmp_path, 'Box')
    run = Run(b, MissingAdapter(), '', tmp_path, 'work')
    wait_for(lambda: not run.active)
    assert run.state()['status'] == 'failed'
    assert 'No such file' in run.state()['detail']
    run.process.stdin.close(); b.close()
