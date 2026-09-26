import json
from pathlib import Path
import pytest
from workbox.storage import Box, write_json


def test_roundtrip_and_no_relocation(tmp_path):
    root = tmp_path / 'project'; root.mkdir()
    material = tmp_path / 'notes.txt'; material.write_text('mine')
    b = Box.create(root, 'Project')
    b.associate(material); b.associate(material)
    assert len(b.data['materials']) == 1
    b.close()
    b = Box(root)
    assert b.data['name'] == 'Project'
    assert material.read_text() == 'mine'
    assert not (root / 'notes.txt').exists()
    b.close()


def test_create_collision_preserves_every_byte(tmp_path):
    b = Box.create(tmp_path, 'First'); b.close()
    before = (tmp_path / '.workbox/box.json').read_bytes()
    with pytest.raises(FileExistsError):
        Box.create(tmp_path, 'Second')
    assert (tmp_path / '.workbox/box.json').read_bytes() == before


def test_exclusive_open(tmp_path):
    b = Box.create(tmp_path, 'Box')
    with pytest.raises(ValueError, match='already open'):
        Box(tmp_path)
    b.close()
    Box(tmp_path).close()


def test_unknown_version_and_invalid_reference(tmp_path):
    b = Box.create(tmp_path, 'Box'); b.close()
    path = tmp_path / '.workbox/box.json'
    data = json.loads(path.read_text()); data['schema_version'] = 99
    write_json(path, data)
    with pytest.raises(ValueError, match='version'):
        Box(tmp_path)
    data['schema_version'] = 1; data['materials'] = [{'path': '../relative'}]
    write_json(path, data)
    with pytest.raises(ValueError, match='absolute'):
        Box(tmp_path)


def test_recovery_preserves_completed_pieces_and_files(tmp_path):
    b = Box.create(tmp_path, 'Box')
    task_dir = b.create_task('work', 'codex', tmp_path)
    path = task_dir / 'task.json'
    task = json.loads(path.read_text())
    task['status'] = 'running'
    task['pieces'].append({'id': 'done', 'worker': 'copilot', 'status': 'completed'})
    write_json(path, task)
    result = tmp_path / 'result.txt'; result.write_text('safe')
    b.close(); b = Box(tmp_path)
    recovered = b.tasks()[0][1]
    assert recovered['status'] == 'interrupted'
    assert recovered['pieces'][1]['status'] == 'completed'
    assert result.read_text() == 'safe'
    b.close()


def test_repository_worktree_and_missing_reference(tmp_path):
    b = Box.create(tmp_path, 'Box')
    repo = tmp_path / 'repo'; repo.mkdir(); (repo / '.git').write_text('gitdir: elsewhere')
    b.associate(repo, 'repository')
    assert b.data['repository'] == str(repo)
    with pytest.raises(FileNotFoundError):
        b.associate(tmp_path / 'missing')
    b.close()


def test_symlink_metadata_rejected(tmp_path):
    other = tmp_path / 'other'; other.mkdir()
    b = Box.create(other, 'Other'); b.close()
    (tmp_path / '.workbox').symlink_to(other / '.workbox', target_is_directory=True)
    with pytest.raises(ValueError):
        Box(tmp_path)


def test_symlink_task_never_mutates_target(tmp_path):
    b = Box.create(tmp_path, 'Box')
    directory = b.create_task('test', 'codex', tmp_path)
    original = directory / 'task.json'
    target = tmp_path / 'external.json'
    original.rename(target)
    original.symlink_to(target)
    before = target.read_bytes()
    b.close()
    with pytest.raises(ValueError, match='Linked task'):
        Box(tmp_path)
    assert target.read_bytes() == before


def test_failed_atomic_replace_preserves_record(tmp_path, monkeypatch):
    path = tmp_path / 'record.json'; write_json(path, {'old': True})
    def fail(*args):
        raise OSError('simulated disk error')
    monkeypatch.setattr('os.replace', fail)
    with pytest.raises(OSError):
        write_json(path, {'new': True})
    assert json.loads(path.read_text()) == {'old': True}
    assert not list(tmp_path.glob('.write-*'))


def test_corrupt_task_releases_box_lock(tmp_path):
    b = Box.create(tmp_path, 'Box')
    directory = b.create_task('test', 'codex', tmp_path)
    path = directory / 'task.json'; original = path.read_text()
    path.write_text('{broken'); b.close()
    with pytest.raises(ValueError, match='Cannot read task'):
        Box(tmp_path)
    path.write_text(original)
    Box(tmp_path).close()
