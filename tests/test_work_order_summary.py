from dataclasses import asdict
import json

import pytest

from workbox.list_work_orders import main, work_order_summary
from workbox.work_orders import STATUSES, WorkOrder


def record(path, status='draft'):
    data = asdict(WorkOrder('Report', status=status))
    path.write_text(json.dumps(data))
    return data


def expected(statuses):
    return {'total': len(statuses),
            'by_status': {s: statuses.count(s) for s in sorted(STATUSES)}}


@pytest.mark.parametrize('statuses', [[], *[[s, s] for s in sorted(STATUSES)],
                                      [*sorted(STATUSES), 'active', 'waiting']])
def test_counts_stable_and_read_only(tmp_path, capsys, monkeypatch, statuses):
    for i, status in enumerate(statuses):
        record(tmp_path / f'{i}.json', status)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    def forbid_write(*args, **kwargs):
        pytest.fail('Reporting must never save')
    monkeypatch.setattr(WorkOrder, 'save', forbid_write)
    assert work_order_summary(tmp_path) == expected(statuses)
    for _ in range(2):
        assert main(['--summary', str(tmp_path)]) == 0
        output = capsys.readouterr()
        assert output.out == json.dumps(expected(statuses), indent=2) + '\n'
        assert not output.err
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}


def test_existing_directory_selection_rules(tmp_path):
    record(tmp_path / 'normal.json')
    (tmp_path / 'notes.txt').write_text('unrelated')
    (tmp_path / 'upper.JSON').write_text('{bad')
    nested = tmp_path / 'nested.json'; nested.mkdir()
    (nested / 'bad.json').write_text('{bad')
    assert work_order_summary(tmp_path) == expected(['draft'])
    (tmp_path / 'unrelated.json').write_text('{"other": true}')
    with pytest.raises(ValueError, match='unrelated.json'):
        work_order_summary(tmp_path)


def test_links_and_duplicate_ids_follow_listing(tmp_path):
    record(tmp_path / 'original.json', 'waiting')
    (tmp_path / 'copy.json').write_bytes((tmp_path / 'original.json').read_bytes())
    (tmp_path / 'link.json').symlink_to(tmp_path / 'original.json')
    (tmp_path / 'broken.json').symlink_to(tmp_path / 'missing')
    assert work_order_summary(tmp_path) == expected(['waiting'] * 3)


@pytest.mark.parametrize('bad', [b'{broken', b'[]', b'{}', b'\xff'])
def test_malformed_records_fail_without_partial_report(tmp_path, capsys, bad):
    record(tmp_path / 'a.json')
    path = tmp_path / 'z.json'; path.write_bytes(bad)
    assert main(['--summary', str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert not output.out and str(path) in output.err
    assert path.read_bytes() == bad


@pytest.mark.parametrize('change', [{'status': 'unknown'}, {'status': 'ACTIVE'},
    {'status': None}, {'status': []}, {'title': ''}, {'schema_version': 2},
    {'id': 'bad'}, {'updated_at': 'bad'}, {'inputs': None}])
def test_invalid_model_data_rejected(tmp_path, capsys, change):
    path = tmp_path / 'bad.json'; data = record(path); data.update(change)
    path.write_text(json.dumps(data)); before = path.read_bytes()
    assert main(['--summary', str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert not output.out and str(path) in output.err
    assert path.read_bytes() == before


@pytest.mark.parametrize('kind', ['missing', 'file', 'permission'])
def test_directory_errors(tmp_path, capsys, monkeypatch, kind):
    path = tmp_path / 'orders'
    if kind == 'file':
        path.write_text('not a directory')
    elif kind == 'permission':
        path.mkdir()
        def deny(*args):
            raise PermissionError('Permission denied')
        monkeypatch.setattr(type(path), 'iterdir', deny)
    assert main(['--summary', str(path)]) == 1
    output = capsys.readouterr()
    assert not output.out and output.err
    if kind == 'missing':
        assert not path.exists()


def test_unreadable_record(tmp_path, capsys, monkeypatch):
    path = tmp_path / 'private.json'; record(path)
    def deny(*args):
        raise PermissionError('Permission denied')
    monkeypatch.setattr(WorkOrder, 'load', deny)
    assert main(['--summary', str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert not output.out and str(path) in output.err and 'Permission denied' in output.err


@pytest.mark.parametrize('extra', [
    ['DIRECTORY'], ['--detail', 'FILE'],
    ['--status', 'active'], ['--update-status', 'FILE'],
])
def test_incompatible_operations_do_not_write(tmp_path, capsys, extra):
    path = tmp_path / 'order.json'; record(path); before = path.read_bytes()
    extra = [str(tmp_path) if a == 'DIRECTORY' else str(path) if a == 'FILE' else a for a in extra]
    with pytest.raises(SystemExit) as exc:
        main(['--summary', str(tmp_path), *extra])
    assert exc.value.code == 2
    assert not capsys.readouterr().out
    assert path.read_bytes() == before


def test_summary_requires_directory(capsys):
    with pytest.raises(SystemExit) as exc:
        main(['--summary'])
    assert exc.value.code == 2
    assert not capsys.readouterr().out


def test_summary_matches_listing_detail_and_filter(tmp_path, capsys):
    path = tmp_path / 'order.json'; record(path, 'completed')
    assert work_order_summary(tmp_path) == expected(['completed'])
    assert main(['--detail', str(path)]) == 0
    detail = json.loads(capsys.readouterr().out)
    assert detail['status'] == 'completed'
    assert main([str(tmp_path)]) == 0
    listing = capsys.readouterr().out
    assert main(['--status', 'completed', str(tmp_path)]) == 0
    assert capsys.readouterr().out == listing
    assert len(json.loads(listing)) == work_order_summary(tmp_path)['total']
