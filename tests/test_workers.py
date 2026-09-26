from unittest.mock import patch
from workbox.workers import WORKERS
import pytest


def test_absent():
    with patch('shutil.which', return_value=None):
        assert WORKERS[0].detect().executable is None


def test_found_version(tmp_path):
    worker = tmp_path / 'codex'
    worker.write_text('#!/bin/sh\necho fake-1.0\n'); worker.chmod(0o700)
    with patch('shutil.which', return_value=str(worker)):
        readiness = WORKERS[0].detect()
    assert readiness.version == 'fake-1.0'
    assert 'authentication not checked' in readiness.detail


def test_arguments_never_use_shell_and_copilot_is_detection_only(tmp_path):
    args = WORKERS[0].launch_args('/bin/codex', tmp_path)
    assert args[args.index('--sandbox') + 1] == 'workspace-write'
    assert args[-1] == '-'
    with pytest.raises(ValueError):
        WORKERS[1].launch_args('/bin/copilot', tmp_path)
