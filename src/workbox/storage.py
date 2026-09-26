"""Versioned JSON and exclusive, advisory Linux Box ownership."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import tempfile
import uuid
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict):
    """Atomically update app-owned metadata; fsync contents and directory."""
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Box:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.meta = self.root / '.workbox'
        self.lock = None
        if self.meta.is_symlink() or not self.meta.is_dir():
            raise ValueError('This folder does not contain a Work Box.')
        try:
            self.data = json.loads((self.meta / 'box.json').read_text())
            self.validate()
            fd = os.open(self.meta / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self.lock = os.fdopen(fd, 'a+')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.close()
            raise ValueError('This Box is already open or a worker is still stopping.') from exc
        except Exception:
            self.close()
            raise
        try:
            self.recover()
        except Exception:
            self.close()
            raise

    def validate(self):
        d = self.data
        if not isinstance(d, dict) or d.get('schema_version') != 1:
            raise ValueError('Unsupported Box metadata version.')
        if not isinstance(d.get('name'), str) or not d['name'].strip():
            raise ValueError('The Box name is missing.')
        if not isinstance(d.get('locations'), list) or not isinstance(d.get('materials'), list):
            raise ValueError('Invalid Box locations or materials.')
        for entry in d['locations'] + d['materials']:
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str) or not Path(entry['path']).is_absolute():
                raise ValueError('Box references must be absolute filesystem paths.')
        if d.get('repository') is not None and (not isinstance(d['repository'], str) or not Path(d['repository']).is_absolute()):
            raise ValueError('Invalid repository path.')
        if (self.meta / 'box.json').is_symlink() or (self.meta / 'tasks').is_symlink():
            raise ValueError('Metadata links are not supported.')

    @classmethod
    def create(cls, root: Path, name: str):
        root = root.expanduser().resolve(strict=True)
        if not root.is_dir() or not name.strip():
            raise ValueError('Choose an existing folder and a nonempty name.')
        meta = root / '.workbox'
        meta.mkdir(mode=0o700)  # Exclusive: never replace an existing file/directory.
        (meta / 'tasks').mkdir()
        write_json(meta / 'box.json', {
            'schema_version': 1, 'id': str(uuid.uuid4()), 'name': name.strip(),
            'locations': [{'path': str(root), 'role': 'project'}],
            'repository': str(root) if (root / '.git').exists() else None,
            'materials': [], 'created_at': now(),
            'time_capsules': {'enabled': False, 'destination': None, 'commits_between': None},
        })
        return cls(root)

    def save(self):
        self.validate()
        write_json(self.meta / 'box.json', self.data)

    def associate(self, path: Path, kind='material'):
        path = path.expanduser().resolve(strict=True)
        if kind in ('location', 'repository') and not path.is_dir():
            raise ValueError('A project location must be a folder.')
        if kind == 'repository' and not (path / '.git').exists():
            raise ValueError('Choose a Git repository root (including a Git worktree).')
        key = 'materials' if kind == 'material' else 'locations'
        if not any(item['path'] == str(path) for item in self.data[key]):
            self.data[key].append({'path': str(path), 'role': kind})
        if kind == 'repository':
            self.data['repository'] = str(path)
        self.save()

    def tasks(self):
        result = []
        for path in sorted((self.meta / 'tasks').glob('*/task.json')):
            try:
                if path.is_symlink() or path.parent.is_symlink():
                    raise ValueError('Linked task metadata is not supported')
                item = json.loads(path.read_text())
                if (not isinstance(item, dict) or item.get('schema_version') != 1
                        or item.get('status') not in ('queued', 'running', 'stopping', 'completed', 'failed', 'interrupted')
                        or not isinstance(item.get('pieces'), list)
                        or not all(isinstance(piece, dict) and 'status' in piece for piece in item['pieces'])
                        or not isinstance(item.get('authorized_workers'), list)
                        or not all(isinstance(worker, str) for worker in item['authorized_workers'])
                        or not isinstance(item.get('created_at'), str)):
                    raise ValueError('Invalid task record')
                result.append((path, item))
            except (OSError, ValueError) as exc:
                raise ValueError(f'Cannot read task record {path}: {exc}') from exc
        return result

    def recover(self):
        # The inherited flock prevents recovery while our supervisor is alive.
        for path, task in self.tasks():
            if task['status'] in ('queued', 'running', 'stopping'):
                task.update(status='interrupted', ended_at=now(), detail='Previous session ended unexpectedly. Review logs and files before starting new work.')
                for piece in task.get('pieces', []):
                    if piece['status'] != 'completed':
                        piece['status'] = 'interrupted'
                write_json(path, task)

    def create_task(self, prompt, worker, cwd):
        if not prompt.strip():
            raise ValueError('Describe the work first.')
        task_id = str(uuid.uuid4())
        directory = self.meta / 'tasks' / task_id
        directory.mkdir()
        context = {'box': self.data, 'working_directory': str(cwd)}
        write_json(directory / 'context.json', context)
        with (directory / 'request.md').open('x') as stream:
            stream.write(prompt.strip() + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        task = {'schema_version': 1, 'id': task_id, 'created_at': now(),
                'authorized_workers': [worker], 'auto_split': 'off', 'halt_requested': False,
                'status': 'queued', 'pieces': [{'id': 'main', 'worker': worker, 'status': 'queued'}]}
        write_json(directory / 'task.json', task)
        return directory

    def close(self):
        if self.lock:
            self.lock.close()
            self.lock = None
