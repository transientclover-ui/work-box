# Contributing

Run `uv sync` and `uv run pytest` before proposing changes. Keep non-UI behavior independent of Qt. Use temporary directories and fake worker programs in tests; do not require provider authentication or paid calls.

Changes must preserve ordinary files, existing organization, explicit worker authorization and durable HALT intent. Do not add credential storage, hidden auto-dispatch, automatic collision renaming or desktop configuration changes. Document schema changes and reject unsupported versions rather than guessing.

See docs/desktop-validation.md for the manual Linux release matrix. Report the desktop, Qt version, worker version and reproduction steps with issues; redact private material from task logs.
