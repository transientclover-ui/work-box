from dataclasses import asdict
import json

import pytest

from workbox.list_work_orders import list_work_orders, main
from workbox.work_orders import STATUSES, WorkOrder


def write_order(path, title, **kwargs):
    order = WorkOrder(title, created_at='2026-01-01T00:00:00+00:00',
                      updated_at='2026-01-02T00:00:00+00:00', **kwargs)
    path.write_text(json.dumps(asdict(order)), encoding='utf-8')
    return order


def test_empty_list(tmp_path, capsys):
    assert list_work_orders(tmp_path) == []
    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == '[]\n'


def test_multiple_orders_stable_output_and_no_writes(tmp_path, capsys):
    second = write_order(tmp_path / 'z.json', 'Second', assigned_worker='Agent B', status='active')
    first = write_order(tmp_path / 'a.json', 'First\n"quoted"\t☃')
    (tmp_path / 'notes.txt').write_text('not an order')
    nested = tmp_path / 'nested'; nested.mkdir()
    (nested / 'invalid.json').write_text('{bad')
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.rglob('*') if p.is_file()}
    assert main([str(tmp_path)]) == 0
    output = capsys.readouterr()
    expected = [dict(id=o.id, title=o.title, status=o.status,
                     assigned_worker=o.assigned_worker, updated_at=o.updated_at) for o in (first, second)]
    assert output.out == json.dumps(expected, indent=2, ensure_ascii=True) + '\n'
    assert output.err == ''
    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == output.out
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.rglob('*') if p.is_file()}


def test_optional_constructor_values_default_to_unassigned(tmp_path):
    write_order(tmp_path / 'order.json', 'Minimal')
    summary, = list_work_orders(tmp_path)
    assert summary['assigned_worker'] is None
    assert summary['status'] == 'draft'


@pytest.mark.parametrize('missing', ['assigned_worker', 'description', 'inputs', 'expected_outputs', 'constraints', 'dependencies'])
def test_omitted_saved_fields_keep_existing_validation(tmp_path, missing, capsys):
    path = tmp_path / 'bad.json'
    order = write_order(path, 'Incomplete')
    data = asdict(order); del data[missing]
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    assert main([str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'bad.json' in output.err
    assert 'schema fields' in output.err
    assert path.read_bytes() == before


def test_invalid_file_no_partial_output(tmp_path, capsys):
    write_order(tmp_path / 'a.json', 'Valid')
    (tmp_path / 'z.json').write_text('{broken')
    assert main([str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'z.json' in output.err


def test_missing_directory_is_not_created(tmp_path, capsys):
    missing = tmp_path / 'missing'
    assert main([str(missing)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'Not a work-order directory' in output.err
    assert not missing.exists()


@pytest.mark.parametrize('status', sorted(STATUSES))
def test_status_filter_mixed_records_and_read_only(tmp_path, capsys, monkeypatch, status):
    for index, value in enumerate(sorted(STATUSES)):
        write_order(tmp_path / f'{index}.json', value, status=value)
    write_order(tmp_path / 'z.json', 'Another match', status=status)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    unfiltered = list_work_orders(tmp_path)
    expected = [row for row in unfiltered if row['status'] == status]

    def forbid_save(*args, **kwargs):
        pytest.fail('Listing must never save')

    monkeypatch.setattr(WorkOrder, 'save', forbid_save)
    assert list_work_orders(tmp_path, status=status) == expected
    for _ in range(2):
        assert main(['--status', status, str(tmp_path)]) == 0
        output = capsys.readouterr()
        assert output.out == json.dumps(expected, indent=2, ensure_ascii=True) + '\n'
        assert output.err == ''
    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == json.dumps(unfiltered, indent=2, ensure_ascii=True) + '\n'
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}


@pytest.mark.parametrize('status', sorted(STATUSES))
@pytest.mark.parametrize('empty', [True, False])
def test_status_filter_zero_matches(tmp_path, capsys, status, empty):
    if not empty:
        other = next(value for value in sorted(STATUSES) if value != status)
        write_order(tmp_path / 'other.json', 'Other', status=other)
    assert main(['--status', status, str(tmp_path)]) == 0
    output = capsys.readouterr()
    assert output.out == '[]\n'
    assert output.err == ''


@pytest.mark.parametrize('status', ['running', 'ACTIVE', ''])
def test_invalid_status_is_usage_error(tmp_path, capsys, status):
    with pytest.raises(SystemExit) as exc:
        main(['--status', status, str(tmp_path)])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.out == ''
    assert 'invalid choice' in output.err
    assert '--status' in output.err
    with pytest.raises(ValueError, match='Invalid work order status'):
        list_work_orders(tmp_path, status=status)


def test_status_rejected_for_detail(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(['--detail', str(tmp_path / 'order.json'), '--status', 'draft'])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.out == ''
    assert '--status cannot be combined with --detail' in output.err


@pytest.mark.parametrize('args', [
    ['--update-status', 'order.json', '--to', 'active'],
    ['--to', 'active'],
])
def test_mutating_options_are_not_available(tmp_path, capsys, args):
    path = tmp_path / 'order.json'
    write_order(path, 'Unchanged')
    before = path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert not capsys.readouterr().out
    assert path.read_bytes() == before


def test_filter_does_not_hide_invalid_nonmatching_record(tmp_path, capsys):
    write_order(tmp_path / 'a.json', 'Valid', status='active')
    path = tmp_path / 'z.json'
    order = write_order(path, 'Invalid', status='draft')
    data = asdict(order); del data['inputs']
    path.write_text(json.dumps(data))
    assert main(['--status', 'active', str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'z.json' in output.err
    assert 'schema fields' in output.err
