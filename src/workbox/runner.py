"""UI-side lifetime handle. A supervisor owns process cleanup and final state."""
import json
import os
from pathlib import Path
import subprocess
import sys
from .storage import now, write_json


class Run:
    def __init__(self, box, adapter, executable, cwd: Path, prompt: str):
        arguments = adapter.launch_args(executable, cwd)
        self.directory = box.create_task(prompt, adapter.id, cwd)
        write_json(self.directory / 'launch.json', {'argv': arguments, 'cwd': str(cwd)})
        try:
            self.process = subprocess.Popen(
                [sys.executable, '-m', 'workbox.supervisor', str(self.directory)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                pass_fds=(box.lock.fileno(),), start_new_session=True)
        except OSError as exc:
            task = json.loads((self.directory / 'task.json').read_text())
            task.update(status='failed', detail=str(exc), ended_at=now())
            task['pieces'][0]['status'] = 'failed'
            write_json(self.directory / 'task.json', task)
            raise

    @property
    def active(self):
        return self.process.poll() is None

    def halt(self):
        # Exclusive durable intent, checked before launch and throughout execution.
        try:
            with (self.directory / 'HALT').open('x') as stream:
                stream.write(now() + '\n')
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            pass
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()

    def state(self):
        return json.loads((self.directory / 'task.json').read_text())
