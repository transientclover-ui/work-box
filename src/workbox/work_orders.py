"""Small, passive work descriptions; no execution or dependency scheduling."""
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
import json
from pathlib import Path
from uuid import UUID, uuid4

from .storage import now, write_json

STATUSES = frozenset({'draft', 'waiting', 'active', 'completed', 'cancelled'})


@dataclass
class WorkOrder:
    title: str
    description: str = ''
    status: str = 'draft'
    assigned_worker: str | None = None
    inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    schema_version: int = 1

    def __post_init__(self):
        self.validate()

    def validate(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError('Unsupported work order schema version')
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError('Work order title must be nonempty text')
        if not isinstance(self.description, str):
            raise ValueError('Work order description must be text')
        if not isinstance(self.status, str) or self.status not in STATUSES:
            raise ValueError('Invalid work order status')
        if self.assigned_worker is not None and (
            not isinstance(self.assigned_worker, str) or not self.assigned_worker.strip()
        ):
            raise ValueError('assigned_worker must be nonempty text or null')
        for name in ('inputs', 'expected_outputs', 'constraints', 'dependencies'):
            value = getattr(self, name)
            if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
                raise ValueError(f'{name} must be a list of nonempty strings')
        for value in [self.id, *self.dependencies]:
            if not isinstance(value, str):
                raise ValueError('Work order IDs must be UUID strings')
            try:
                if str(UUID(value)) != value:
                    raise ValueError('Use canonical UUID strings')
            except (ValueError, AttributeError) as exc:
                raise ValueError('Work order IDs must be canonical UUID strings') from exc
        if self.id in self.dependencies or len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError('Dependencies must be unique and cannot reference this order')
        dates = []
        for name in ('created_at', 'updated_at'):
            value = getattr(self, name)
            try:
                date = datetime.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f'{name} must be an ISO 8601 timestamp') from exc
            if date.utcoffset() is None:
                raise ValueError(f'{name} must include a timezone')
            dates.append(date)
        if dates[1] < dates[0]:
            raise ValueError('updated_at cannot precede created_at')

    @classmethod
    def load(cls, path: Path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        names = {item.name for item in fields(cls)}
        if not isinstance(data, dict) or set(data) != names:
            raise ValueError('Work order must contain exactly the documented schema fields')
        return cls(**data)

    def save(self, path: Path, *, overwrite: bool = False):
        """Create exclusively; explicitly overwrite only a matching existing order.

        Callers serialize edits. This is not a concurrent multi-writer store.
        """
        self.validate()
        path = Path(path)
        timestamp = now()
        if datetime.fromisoformat(timestamp) < datetime.fromisoformat(self.created_at):
            raise ValueError('Creation timestamp is in the future')
        data = asdict(self)
        data['updated_at'] = timestamp
        if overwrite:
            if path.is_symlink():
                raise ValueError('Linked work order files cannot be updated')
            original = self.load(path)
            if (original.id, original.created_at) != (self.id, self.created_at):
                raise ValueError('Cannot replace a different work order or its creation timestamp')
            write_json(path, data)
        else:
            # Exclusive creation never replaces a user's existing file.
            with path.open('x', encoding='utf-8') as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False)
                stream.write('\n')
        self.updated_at = timestamp
