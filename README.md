# Work Box

A small native Linux desktop application for keeping project materials and installed AI workers together. Your files stay yours: a Box references ordinary folders and files wherever they already live.

**Foundation release · 0.1.0 · MIT license**

## Run

Requires Linux, Python 3.11+, and a functioning Qt 6 desktop runtime. From this repository:

```sh
uv sync
uv run work-box
# Optionally open an existing Box:
uv run work-box /path/to/project
```

Alternatively create a virtual environment and `pip install -e .`. No desktop configuration or system installation is required. The optional desktop entry in `share/` is a template, not automatically installed.

## Use

1. Create Box: select an existing folder for its `.workbox` metadata, then name it. An existing `.workbox` is never replaced; use Open Box instead.
2. Associate project folders or a Git repository. Add files or drop files/folders to reference them in place. No copying or relocation happens.
3. Select an installed worker. This release detects Codex and GitHub Copilot; only Codex execution is enabled. Authenticate in the worker's own terminal interface first.
4. Choose the working folder and describe the work, including which files may change. Give Work starts a noninteractive Codex run with the workspace-write sandbox. The worker's own configuration, installed integrations, and policies still apply. Extra Box locations are context references, not automatically granted write roots.
5. HALT stops the managed process group and preserves files already written. Closing the window also halts. Double-click a task to open its request, context and log folder in the normal file manager.

System appearance is the default. Light/Dark overrides use Qt's color-scheme API. System fonts, palettes, icons and dialogs depend on available platform integration; Work Box never changes the desktop theme. A bundled PySide6 Qt may not load distribution plugins with a different Qt ABI. See the architecture document for packaging caveats.

## Durable files

```text
chosen-folder/
  .workbox/
    box.json                 # versioned metadata, absolute references
    lock                     # advisory exclusive ownership
    tasks/<uuid>/
      task.json              # authorized workers, pieces, status, timestamps
      request.md             # original request
      context.json           # Box context at launch
      input.md               # exact worker input
      launch.json            # argument list and working folder (no credentials)
      worker.log             # merged stdout/stderr; contains worker result
      HALT                   # optional durable stop intent
```

Deleting Work Box does not delete project materials. Metadata is plain JSON/Markdown; no database or proprietary project container is involved. Moving a referenced path requires updating its association. Logs can contain sensitive project content: review before sharing. Work Box does not collect or store provider credentials or copy worker authentication files.

## Development

```sh
uv sync
uv run pytest
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_ui.py
```

Tests use temporary directories and fake workers; they make no paid AI requests. See [architecture](docs/architecture.md), [development journal](docs/journal.md), and [desktop validation checklist](docs/desktop-validation.md).

## Deliberate boundaries

Copilot launch, interactive approval handling, resume UI, copying materials, task splitting, parallel workers, failover, and ZIP Time Capsules are not implemented. The model reserves multi-worker and capsule contracts. Exit code zero means the worker completed its process, not that Work Box has verified its work.

Process groups handle normal descendants, not children that deliberately detach into new sessions. A separate watchdog handles GUI death; simultaneous watchdog failure can leave descendants and is not a containment guarantee. Future cgroup integration must remain optional and must not modify system services. Network filesystem locking and power-loss behavior are not certified. Use a local filesystem for metadata in this release.
