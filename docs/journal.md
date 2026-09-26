# Development journal

## 2026-09-26 · Foundation checkpoint

### Scope and decisions

Built the first dogfoodable shell only. Chose Python 3.11+ / Qt 6 Widgets (PySide6) after comparing Qt Widgets, Qt Quick, GTK/libadwaita, and web stacks. Native platform integration and a small independent filesystem/process core outweighed a custom visual stack. See architecture.md for sources, tradeoffs and packaging caveats.

Created an MIT-licensed Python package with an executable entry point, dependency lock, independent storage/worker/process modules, tests, documentation and an optional desktop-entry template. No desktop entry was installed. No desktop, Omarchy, KDE, system service, package trust, login/session settings or existing repositories were changed. Dependencies were installed in the project virtual environment.

A Box uses an exclusive `.workbox` directory in a user-selected existing folder and absolute file/folder references. It never moves source materials, invents collision names, creates standard project folders, or reinitializes Git. Versioned JSON, atomic replacement and an advisory lock supply a deliberately small persistence boundary.

Enabled one Codex process at a time, with durable request/context/input/log/status records. The supervisor holds the Box lock, watches a parent pipe, and handles process-group termination. Copilot is detected but launch remains disabled until permissions and interaction are designed. No provider credentials are read or stored by Work Box.

### Validation completed

- **21 tests passed** (`uv run pytest -q`, 2.74 seconds on this machine).
- Storage: round trip; deduplicated in-place references; collision preservation; concurrent-open rejection; schema validation; Git worktree association; missing references; linked metadata refusal; interrupted-task recovery preserving completed pieces; failed atomic replace preserving the previous record; lock release after malformed task metadata.
- Workers: absent executable, installed version probe, safe argument construction and explicit Copilot launch rejection.
- Processes: successful durable output/context; nonzero exit; missing executable; immediate HALT; repeated HALT; TERM-resistant parent/child process group cleanup; existing result preservation; inherited lock; parent-pipe disconnect simulating GUI failure.
- UI: offscreen shell construction, Box population, appearance API calls and synthetic file drop preserving source files.
- Real desktop: launched and closed a Qt **Wayland** window on the current **KDE** session, populated from temporary test files. Captured and visually inspected `shell.png` for layout/readability. Detected `codex-cli 0.155.1` and `GitHub Copilot CLI 1.0.88.` without starting an AI task.
- Packaging: `uv build` produced both source archive and wheel successfully. The editable install and console entry point are available in `.venv`.

An initial editable build failed because README.md had not yet been written; completed the README and rebuilt successfully. No unresolved build/test failures remain.

### Limits and remaining work

This is an early local prototype, not a desktop-certified release. Hyprland interaction, actual file-manager drag/drop, native dialogs, runtime system-theme switching and a real authenticated Codex task remain manual checks. Theme overrides use Qt hints and can be ignored by external styles. Bundled Qt versus system plugin ABI needs distribution packaging validation.

Worker readiness means installed/version available, not authenticated or funded. A zero exit status is not verification of task quality. Logs carry the durable worker result; no separate structured handoff/result index is enforced. No paid AI execution was performed during development.

Process-group shutdown covers ordinary descendants; deliberately detached children or simultaneous supervisor failure remain limitations. No systemd service/cgroup setup was added. Recovery marks abandoned tasks interrupted and never restarts work automatically. Actual machine power loss and network filesystems were not tested. Disk errors may prevent final task status persistence, though cleanup still attempts to kill the managed group.

Multi-worker authorization/piece fields and Time Capsule protocols are **design-only**. No splitter, scheduler, failover, capsule archives, copying/import, interactive approvals or resume UI exists. Original prompt/context/logs support manual continuation; automatic resumption is deliberately absent.

### Next smallest useful task

Add an explicit **Continue interrupted work** flow: create a new linked attempt from the saved request/context/logs, let the user review the handoff and working directory, and start only after Give Work. Verify that completed artifacts remain untouched unless the new task explicitly authorizes changes. This closes the smallest practical durability gap without adding orchestration.

### Checkpoint

This journal, implementation, tests, lockfile and inspected shell image are included in the local Git commit named `Foundation: native Work Box shell and durable task lifecycle`. No remote repository or publication was created. Session ends at that checkpoint; the next task above has not been started.
