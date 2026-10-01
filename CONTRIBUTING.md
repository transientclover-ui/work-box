# Contributing

Work Box is complete at its deliberately narrow, read-only shared-state scope.
Bug fixes, compatibility fixes, documentation corrections, and validation
improvements are welcome when they preserve that scope.

Before proposing a change:

```sh
uv sync
uv run pytest -q
uv build
git diff --check
```

Keep the runtime independent of GUI toolkits and external services. Preserve the
documented WorkOrder schema, deterministic JSON output, full-record validation,
read-only CLI behavior, and exit codes.

Agent execution, supervision, orchestration, arbitration, quarantine, automated
repair, recovery, and migration are intentionally out of scope.
