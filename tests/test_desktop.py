from pathlib import Path
import shutil
import subprocess

import pytest

from workbox.desktop import install, quote_exec


def test_registration_uses_installed_executable_and_xdg(tmp_path, monkeypatch):
    executable = tmp_path / 'an environment' / 'bin/work-box'
    executable.parent.mkdir(parents=True)
    executable.write_text('#!/bin/sh\nexit 0\n')
    executable.chmod(0o755)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    entry = install(executable)
    assert entry == tmp_path / 'data/applications/work-box.desktop'
    content = entry.read_text()
    assert f'Exec="{executable}"\n' in content
    assert 'Path=' not in content
    assert 'Icon=folder\n' in content
    assert install(executable).read_text() == content
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', str(entry)], check=True)


def test_default_location_and_invalid_install(tmp_path, monkeypatch):
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path))
    executable = tmp_path / 'work-box'
    with pytest.raises(ValueError, match='No installed executable'):
        install(executable)
    executable.touch()
    executable.chmod(0o755)
    assert install(executable) == tmp_path / '.local/share/applications/work-box.desktop'
    monkeypatch.setenv('XDG_DATA_HOME', 'relative')
    with pytest.raises(ValueError, match='absolute'):
        install(executable)


def test_exec_escaping():
    assert quote_exec(Path('/tmp/a b%/work-box')) == '"/tmp/a b%%/work-box"'
    assert quote_exec(Path('/tmp/$x/work-box')) == '"/tmp/\\\\$x/work-box"'
    for value in ('/tmp/a=b/work-box', '/tmp/a\nb/work-box'):
        with pytest.raises(ValueError):
            quote_exec(Path(value))
