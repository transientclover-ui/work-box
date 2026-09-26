# Architecture and decisions

## Stack decision · 2026-09-26

| Candidate | Linux integration | Foundation cost | Decision |
| --- | --- | --- | --- |
| Qt 6 Widgets / PySide6 | Wayland backend; platform fonts, palettes, icons, native dialogs; KDE platform theme integration | Small Python core, mature widgets, no browser runtime | Selected |
| GTK 4 / libadwaita | Native Wayland; strongest GNOME conventions; libadwaita imposes more of its own design language | Viable, but additional work to follow KDE's appearance | Not selected |
| Qt Quick / C++ or Python | Same platform layer; greater freedom for animation/custom controls | More visual infrastructure than this restrained shell needs | Revisit only for a demonstrated UX need |
| Electron / Tauri | Desktop integration possible via web frontend and bridges | Unnecessary web UI, theme and process bridging | Not selected |

Python 3.11+ with PySide6 keeps filesystem/process logic small and independently testable. MIT covers Work Box; PySide6/Qt retain their own licenses (including LGPL/commercial terms). Distribution must include dependency notices and meet applicable Qt licensing requirements. No installer or redistribution bundle is shipped yet.

Qt's [platform abstraction](https://doc.qt.io/qt-6/qpa.html) supports Wayland and platform themes. KDE supplies a [Qt platform-theme integration](https://github.com/KDE/plasma-integration). Work Box follows whichever integration is present; it does not install theme plugins or change environment configuration. [QStyleHints colorScheme](https://doc.qt.io/qt-6/qstylehints.html#colorScheme-prop) supplies System/Light/Dark hints, whose support depends on the backend/style. Some third-party styles can ignore overrides.

On Plasma, use a distribution-matched Qt/PySide6 for best plugin integration. On Hyprland, use the user's existing Qt platform theme/portal setup. A pip wheel bundles Qt and can be ABI-incompatible with system theme plugins. System palette/accent integration is therefore best effort, not a hard-coded imitation of KDE or Omarchy. Runtime appearance changes and overrides require a real-desktop release matrix before promising parity.

## Boundaries

- `storage.py`: plain JSON metadata, path references, exclusive creation, atomic metadata replacement, advisory Box ownership, conservative recovery.
- `workers.py`: installed-program identity/version probing and launch argument adapter. No credential access, provider SDK, token accounting, or authentication broker.
- `runner.py`: task creation, supervisor lifetime and HALT intent.
- `supervisor.py`: durable state writer and managed POSIX process group lifecycle. Uses argument arrays, never shell interpolation.
- `app.py`: Qt widgets, native dialogs, desktop folder opening, drag/drop association, async worker detection, status polling.
- `capsules.py`: future interface only. No archive creation or restoration implementation.

## Filesystem ownership

A Box anchor is an existing user-selected directory containing a newly created `.workbox`. Metadata paths are independent of the logical collection: all project locations and materials are absolute references. Work Box never creates Documents/Pictures/Videos trees, copies files, renames collisions, initializes repositories, or rewrites Git configuration. Git worktrees are accepted via their `.git` file.

Create uses exclusive directory creation. Open rejects unknown schema versions and linked metadata, acquires `flock`, and then recovers unfinished records. App-owned JSON replacement uses a temporary file, fsync, rename, and directory fsync. External material paths may be symlinks; association resolves them to their current target. Missing references remain visible. Editing metadata externally while the app is open is unsupported; close the Box first. Advisory locks only coordinate cooperating Work Box instances.

There is no proprietary project format: the JSON is an index, not the user's work. The initial UI references materials only. Future copy/import must offer an explicit destination and collision policy; never automatically invent `Project (1)`.

## Workers and tasks

Installed worker versions are probed with a three-second timeout off the GUI thread. Readiness explicitly distinguishes installed from authenticated; no network auth probe is made. Codex uses [noninteractive execution](https://learn.chatgpt.com/docs/non-interactive-mode) and the locally validated CLI flags: `exec --sandbox workspace-write --skip-git-repo-check --color never -C <folder> -`. The task/context goes through stdin. We do not select a model, store credentials, or bypass sandbox/approval trust. The worker's own configuration and integrations apply. This is not an independent security boundary, and Work Box cannot enforce how a worker edits a user-authorized workspace.

GitHub Copilot uses its standalone `copilot --version` for detection. Its [programmatic mode](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically) needs an intentional permission/interaction UX before enabling execution. Legacy `gh copilot` is not treated as a substitute.

Each task stores an array of authorized workers, an array of pieces with worker/status, and `auto_split: off`. Future allowed policies are off/ask/automatic. Only one main piece is dispatched now. A completion means zero worker exit status; the UI does not claim semantic correctness. The complete worker stream contains the final response and any result paths. Context and original request are retained so another worker can eventually continue without relying on a conversation ID.

Future scheduling must first consult durable task-wide HALT intent. No new assignment or failover after HALT; completed pieces remain completed, interrupted pieces remain resumable from artifacts. Resume UI, artifact indexing and structured handoffs are future work.

## HALT and recovery

The GUI starts a supervisor inheriting the Box's lock descriptor. The supervisor starts the worker in a fresh process group. GUI stdin-pipe closure, a durable HALT marker, or supervisor SIGTERM/SIGINT requests shutdown. It signals the whole group with TERM, allows two seconds, then sends KILL to remaining members. No result deletion or rollback occurs. Even a normal worker exit triggers descendant cleanup before the supervisor exits and releases its lock.

Closing the app requests HALT and waits asynchronously. If the GUI crashes, EOF on the pipe triggers the same stop path. On reopen, the lock prevents takeover while the supervisor is alive; abandoned queued/running/stopping records become interrupted. PIDs in old records are never blindly signaled, avoiding PID-reuse damage.

Limitations: deliberately detached descendants evade process groups. Simultaneous supervisor death can leave unmanaged processes; recovery does not prove those processes are gone. No crash-proof containment claim is made. Filesystem full errors can prevent final status persistence, though supervisor exception cleanup kills the managed group. No resume or auto-dispatch happens on reopen. A local metadata filesystem is required for this release; network FS and real power-loss testing remain pending.

## Time Capsules contract (not implemented)

`CapsulePlan` names the entire logical Box sources and user-selected destination, optional archive size cap, and Git state. Future manifests must record source-to-entry mappings, hashes, timestamps, repository commit/dirty state (including untracked files), worker/task information, missing sources and exclusions. Archives are ordinary independently readable ZIPs with a manifest in each; repository commits and archives serve different purposes.

Restore must inspect first, reject path traversal and symlink escapes, allow selective restore to a new destination, and refuse collisions. Future optional commit-count triggers must count actual commits, coordinate snapshot consistency with active writes, and honor explicit opt-in. None of these operations runs in this release.
