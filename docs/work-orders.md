# WorkOrder format and CLI

## JSON record

Each file contains exactly these fields:

| Field | Type | Meaning |
|---|---|---|
| `title` | nonempty string | Human-readable work title |
| `description` | string | Work description |
| `status` | string | `active`, `cancelled`, `completed`, `draft`, or `waiting` |
| `assigned_worker` | string or null | Informational agent/worker label |
| `inputs` | array of nonempty strings | Input descriptions or references |
| `expected_outputs` | array of nonempty strings | Expected result descriptions |
| `constraints` | array of nonempty strings | Constraints readers should observe |
| `dependencies` | array of canonical UUID strings | Other WorkOrder IDs |
| `id` | canonical UUID string | Stable record identity |
| `created_at` | ISO 8601 string with timezone | Creation time |
| `updated_at` | ISO 8601 string with timezone | Last producer update |
| `schema_version` | integer `1` | Format version |

Dependencies must be unique and cannot contain the record's own ID.
`updated_at` cannot precede `created_at`. Unknown or missing fields are rejected.
Referenced paths and dependency IDs are labels only; inspection never opens or
resolves them.

See [`examples/work-order.json`](../examples/work-order.json) for a complete
record.

## Commands

### List

```sh
work-box-orders /path/to/work-orders
```

Returns an array of summaries with `id`, `title`, `status`, `assigned_worker`,
and `updated_at`. Immediate lowercase `.json` regular-file entries are read in
filename order. Output is `[]` for an empty directory.

### Filter by status

```sh
work-box-orders --status waiting /path/to/work-orders
```

Uses the model's status vocabulary and returns the same summary shape. Every
discovered record is still validated, including nonmatching records. No matches
is a successful `[]`.

### Detail

```sh
work-box-orders --detail /path/to/order.json
```

Returns every validated WorkOrder field. Only the selected file is read.

### Status summary

```sh
work-box-orders --summary /path/to/work-orders
```

Example:

```json
{
  "total": 3,
  "by_status": {
    "active": 1,
    "cancelled": 0,
    "completed": 1,
    "draft": 1,
    "waiting": 0
  }
}
```

`by_status` always contains all valid statuses in alphabetical order. Empty
directories return `total: 0` with every count set to zero.

## Exit behavior

| Exit | Meaning |
|---|---|
| `0` | Complete successful JSON result |
| `1` | Input directory/file, decoding, JSON, or model-validation failure |
| `2` | Invalid command usage or option combination |

Failures emit no partial JSON. Diagnostics go to stderr. Output formatting and
status ordering are deterministic.

## Read-only guarantee

All public CLI operations are read-only. They do not create, update, repair,
quarantine, migrate, execute, or recover work orders. External producers may
write records using ordinary filesystem tools or the model's save helper; the CLI
only validates and reports the state it reads.
