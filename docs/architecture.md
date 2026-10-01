# Architecture

Work Box is a pure-stdlib Python package with one model and one read-only CLI.

## Components

- `workbox.work_orders` defines the versioned `WorkOrder` dataclass, valid status
  vocabulary, field validation, JSON loading, and producer-side save helper.
- `workbox.list_work_orders` implements deterministic directory discovery plus
  list, status-filter, detail, and status-count output.
- `workbox.storage` contains the timestamp and atomic JSON-write helpers used by
  the model's producer-side save API.
- `work-box-orders` is the only installed command.

All CLI reads pass through `WorkOrder.load`; there is no parallel parser.
Directory operations inspect immediate lowercase `.json` regular-file entries in
filename order. A followed symlink to a regular file participates under normal
filesystem semantics; broken links, subdirectories, and other extensions do not.

## Read boundary

Every selected record must contain exactly the documented fields and pass the
same model validation. Directory operations validate all discovered records
before producing success output, including records excluded by a status filter.
One invalid record therefore fails the operation instead of yielding a
success-shaped partial result.

Success is deterministic JSON on stdout. Content or I/O failure is stderr plus
exit `1`; argument misuse is exit `2`. CLI reads never call the save path.

## Deliberate boundary

Work Box shares state; it does not control agents. There is no worker adapter,
process runner, supervisor, GUI, scheduler, arbitration layer, quarantine,
repair, recovery, migration, or autonomous action.

Earlier development explored a Qt desktop process manager and broader project-box
ideas. Those designs are superseded and are not part of the stable product.
