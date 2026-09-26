"""Adapters discover installed tools; authentication belongs to those tools."""
from dataclasses import dataclass
import shutil
import subprocess
from pathlib import Path


@dataclass(frozen=True)
class Readiness:
    executable: str | None
    version: str
    detail: str


@dataclass(frozen=True)
class WorkerAdapter:
    id: str
    name: str
    command: str
    can_launch: bool = False

    def detect(self):
        executable = shutil.which(self.command)
        if not executable:
            return Readiness(None, '', 'Not installed / not on PATH')
        try:
            result = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=3)
            version = (result.stdout or result.stderr).strip().splitlines()[0][:160]
            detail = 'Installed · authentication not checked'
            if result.returncode:
                detail = 'Installed · version check failed'
            return Readiness(executable, version, detail)
        except (OSError, subprocess.TimeoutExpired, IndexError):
            return Readiness(executable, '', 'Installed · version unavailable')

    def launch_args(self, executable: str, cwd: Path):
        if self.id != 'codex' or not self.can_launch:
            raise ValueError('This worker supports detection only in this release.')
        return [executable, 'exec', '--sandbox', 'workspace-write', '--skip-git-repo-check',
                '--color', 'never', '-C', str(cwd), '-']


WORKERS = [WorkerAdapter('codex', 'Codex', 'codex', True),
           WorkerAdapter('copilot', 'GitHub Copilot', 'copilot')]
