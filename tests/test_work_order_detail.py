from dataclasses import asdict
import json

import pytest

from workbox.list_work_orders import main, work_order_detail
from workbox.work_orders import WorkOrder


def record(path, **kwargs):
    order = WorkOrder('Inspect "source" ☃', description='First line\nSecond line',
                      inputs=['missing/source'], expected_outputs=['report.md'],
                      constraints=['Read only'],
                      created_at='2026-01-01T00:00:00+00:00',
                      updated_at='2026-01-02T00:00:00+00:00', **kwargs)
    path.write_text(json.dumps(asdict(order)), encoding='utf-8')
    return order


@pytest.mark.parametrize('worker', [None, 'Agent A'])
def test_complete_stable_detail_without_writes(tmp_path, capsys, monkeypatch, worker):
    path = tmp_path / 'selected.json'
    order = record(path, assigned_worker=worker, dependencies=[WorkOrder('Earlier').id])
    # Only the selected record is inspected; unrelated malformed records are ignored.
    (tmp_path / 'other.json').write_text('{broken')
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}

    def forbid_save(*args, **kwargs):
        pytest.fail('Detail inspection must never save')

    monkeypatch.setattr(WorkOrder, 'save', forbid_save)
    assert work_order_detail(path) == asdict(order)
    for _ in range(2):
        assert main(['--detail', str(path)]) == 0
        output = capsys.readouterr()
        assert output.out == json.dumps(asdict(order), indent=2, ensure_ascii=True) + '\n'
        assert output.err == ''
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}


@pytest.mark.parametrize('bad', ['{broken', '[]', '{}', '\ufffd'])
def test_malformed_record(tmp_path, capsys, bad):
    path = tmp_path / 'bad.json'
    path.write_text(bad)
    assert main(['--detail', str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert f'Cannot read work order {path}' in output.err
    assert path.read_text() == bad


@pytest.mark.parametrize('change', [
    {'id': 'invalid'}, {'status': 'running'}, {'title': ''},
    {'assigned_worker': 1}, {'description': None}, {'inputs': 'file'},
    {'expected_outputs': [None]}, {'constraints': [1]},
    {'schema_version': 2}, {'unexpected': True},
    {'created_at': 'yesterday'}, {'updated_at': '2000-01-01T00:00:00+00:00'},
])
def test_model_validation_is_preserved(tmp_path, capsys, change):
    path = tmp_path / 'invalid.json'
    data = asdict(record(path)); data.update(change)
    path.write_text(json.dumps(data))
    assert main(['--detail', str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert str(path) in output.err
    assert json.loads(path.read_text()) == data


@pytest.mark.parametrize('kind', ['missing', 'directory', 'encoding'])
def test_unreadable_record(tmp_path, capsys, kind):
    path = tmp_path / 'order.json'
    if kind == 'directory':
        path.mkdir()
    elif kind == 'encoding':
        path.write_bytes(b'\xff')
    assert main(['--detail', str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert str(path) in output.err
    assert 'Traceback' not in output.err
    if kind == 'missing':
        assert not path.exists()


def test_permission_error(tmp_path, capsys, monkeypatch):
    def denied(path):
        raise PermissionError('Permission denied')
    monkeypatch.setattr(WorkOrder, 'load', denied)
    assert main(['--detail', str(tmp_path / 'private.json')]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'Permission denied' in output.err


@pytest.mark.parametrize('args', [[], ['--detail'], ['orders', '--detail', 'order.json']])
def test_selection_usage_errors(args, capsys):
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('field', list(WorkOrder.__dataclass_fields__))
def test_missing_saved_field_rejected(tmp_path, capsys, field):
    path = tmp_path / 'incomplete.json'
    data = asdict(record(path)); del data[field]
    path.write_text(json.dumps(data))
    assert main(['--detail', str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'schema fields' in output.err
