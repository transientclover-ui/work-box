# Work Box

Work Box is a small, finished tool for giving multiple AI agents a common,
inspectable view of work-order state. It intentionally stops at shared visibility
and predictable inspection rather than attempting to orchestrate, supervise, or
autonomously coordinate agents.

Work orders are ordinary JSON files. Any agent or person with filesystem access
can read the same records with normal tools, while `work-box-orders` provides
strict validation and deterministic machine-readable output.

**Stable release · v0.1.0 · MIT license**

## Install

Work Box requires Python 3.11 or newer and has no third-party Python runtime
package dependencies.

[Open Work Box in OmaStore](omastore://transientclover-ui/work-box), or search
OmaStore for **Work Box** (`transientclover-ui/work-box` on GitHub).

The v0.1.0 OmaStore archive supports Linux x86_64. Its launcher uses system
`python3` (3.11+), `/bin/sh`, and `dirname`; Python is not bundled. No daemon or
service is required. No ARM64 application archive is published.

The release asset `work_box-0.1.0-source.tar.gz` is the Python source distribution,
not an OmaStore application archive. Its contents are unchanged from the former
`work_box-0.1.0.tar.gz` asset.

```sh
uv tool install git+https://github.com/transientclover-ui/work-box.git@v0.1.0
# or
python -m pip install git+https://github.com/transientclover-ui/work-box.git@v0.1.0
```

From a source checkout:

```sh
uv sync
uv run work-box-orders --help
```

The Linux release archive contains the application sources and an executable
launcher. It can be extracted into a user-owned directory and run without
installing the Python package:

```sh
./work-box-0.1.0-linux-x86_64/bin/work-box-orders --help
```

## Inspect shared work

List validated records in deterministic filename order:

```sh
work-box-orders /path/to/work-orders
```

Filter the listing using the model's status vocabulary:

```sh
work-box-orders --status active /path/to/work-orders
```

Read one complete validated record:

```sh
work-box-orders --detail /path/to/work-orders/order.json
```

Count every status, including zero-count statuses:

```sh
work-box-orders --summary /path/to/work-orders
```

Successful commands emit JSON on stdout. Invalid command usage exits `2`.
Missing, unreadable, malformed, or model-invalid input exits `1`, writes a
diagnostic to stderr, and emits no partial JSON.

Listing, filtering, detail inspection, and summaries are read-only. They do not
save records, change timestamps, start workers, or resolve referenced paths.

## WorkOrder format

The format records a stable UUID, title, description, status, optional assigned
worker label, input/output descriptions, constraints, dependency IDs, timestamps,
and schema version. The five valid statuses are:

```text
active
cancelled
completed
draft
waiting
```

See [WorkOrder format and CLI](docs/work-orders.md) and the
[example record](examples/work-order.json).

## Finished scope

Work Box provides:

- a versioned, human-readable WorkOrder JSON format;
- strict full-record validation through one shared model;
- deterministic list, status-filter, detail, and status-count JSON output;
- predictable error and exit-code behavior;
- a pure-stdlib runtime suitable for local tools and AI-agent workflows.

Work Box does **not** execute work orders, launch or supervise agents, arbitrate
between agents, quarantine output, repair files, recover work automatically, or
coordinate multi-agent activity. Those larger concepts are outside the product,
not missing milestones.

## Development

```sh
uv sync
uv run pytest -q
uv build
git diff --check
```

The project architecture is documented in [docs/architecture.md](docs/architecture.md).
Historical development decisions are retained in
[docs/journal.md](docs/journal.md) with superseded concepts clearly marked.
