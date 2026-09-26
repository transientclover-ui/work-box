"""Design contract only; snapshot creation/restoration is deliberately absent."""
from dataclasses import dataclass, field
from typing import Protocol
from pathlib import Path


@dataclass(frozen=True)
class CapsulePlan:
    box_id: str
    destination: Path
    sources: tuple[Path, ...]
    max_archive_bytes: int | None = None
    git_state: dict = field(default_factory=dict)
    # Each ZIP is independently readable; manifest maps source paths to entries.
    format: str = 'zip'


class CapsuleBackend(Protocol):
    def inspect(self, archives: tuple[Path, ...]) -> dict: ...
    def create(self, plan: CapsulePlan) -> tuple[Path, ...]: ...
    def restore_selected(self, archives: tuple[Path, ...], entries: tuple[str, ...],
                         destination: Path) -> None:
        """Restore to a new destination, rejecting traversal and collisions."""
        ...
