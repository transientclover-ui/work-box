import json
from pathlib import Path

import pytest

from workbox.work_orders import WorkOrder


def test_create_and_load(tmp_path):
    path = tmp_path / 'order.json'
    order = WorkOrder('Inventory', inputs=['src/'], expected_outputs=['inventory.md'],
                      constraints=['Do not modify source'], dependencies=[WorkOrder('First').id])
    order.save(path)
    loaded = WorkOrder.load(path)
    assert loaded == order


def test_preserve_existing_files_and_identity(tmp_path):
    path = tmp_path / 'order.json'
    order = WorkOrder('First'); order.save(path)
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        WorkOrder('Second').save(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('change', [
    {'title': ''}, {'description': None}, {'status': 'running'},
    {'assigned_worker': ''}, {'inputs': 'file'}, {'constraints': [1]},
    {'expected_outputs': [None]}, {'dependencies': ['not-a-uuid']},
    {'schema_version': 2}, {'schema_version': True}, {'id': 'bad'},
    {'created_at': 'yesterday'}, {'updated_at': '2020-01-01T00:00:00'},
    {'updated_at': '2000-01-01T00:00:00+00:00'},
])
def test_invalid_records_rejected(tmp_path, change):
    path = tmp_path / 'order.json'; WorkOrder('Valid').save(path)
    data = json.loads(path.read_text()); data.update(change)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        WorkOrder.load(path)


def test_dependencies_and_independent_defaults():
    a, b = WorkOrder('A'), WorkOrder('B')
    a.inputs.append('source')
    assert b.inputs == []
    a.dependencies = [a.id]
    with pytest.raises(ValueError):
        a.validate()
    a.dependencies = [b.id, b.id]
    with pytest.raises(ValueError):
        a.validate()


def test_missing_unknown_and_malformed_fields(tmp_path):
    path = tmp_path / 'order.json'; WorkOrder('Valid').save(path)
    data = json.loads(path.read_text())
    for bad in ({**data, 'unknown': True}, {k: v for k, v in data.items() if k != 'id'}, []):
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError):
            WorkOrder.load(path)
    path.write_text('{broken')
    with pytest.raises(ValueError):
        WorkOrder.load(path)


def test_example():
    example = Path(__file__).resolve().parents[1] / 'examples/work-order.json'
    assert WorkOrder.load(example).status == 'draft'
