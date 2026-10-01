# Development journal

## 2026-09-26 · Original desktop experiment

The initial public beta explored a Qt desktop shell that associated project files
and launched a managed Codex process. It included worker detection, process-group
HALT behavior, task logs, and design placeholders for broader automation.

That direction is superseded. It did not match the finished product's deliberately
small shared-state purpose, and the desktop runner, worker adapters, supervisor,
recovery behavior, and speculative orchestration concepts were removed before the
stable release.

## 2026-09-27 · Shared WorkOrder format

Added the versioned `WorkOrder` JSON model and deterministic read-only directory
listing. Full saved-record validation rejects missing, unknown, malformed, or
invalid fields through one model path.

Added complete single-record detail output, optional status filtering using the
model vocabulary, and a status-count summary containing every valid status,
including zero-count statuses. Empty directories produce valid empty results.
Malformed records fail without partial JSON.

An explicit status-update CLI was briefly developed after filtering. It was
removed from the stable product so every shipped command remains read-only.

## 2026-10-01 · Stable product finalization

Selected shared WorkOrder checkpoint `0de60b6` as the functional baseline.
Discarded later local-only integrity, forensic, diagnostic-schema, report-loader,
and speculative project-box work. Removed the inherited desktop application,
agent execution, supervision, recovery, and status-mutation command.

Repositioned Work Box as a complete shared-state inspection tool. The stable
package contains the WorkOrder model and deterministic list, filter, detail, and
summary CLI only. It has no runtime package dependencies and does not execute,
coordinate, arbitrate, quarantine, repair, or recover agent work.

The development phase is complete at this scope. There is no core-feature queue;
future repository activity is limited to compatible maintenance.

Final validation passed **121 tests**. Source and wheel builds succeeded, and a
fresh environment outside the checkout exercised the installed
`work-box-orders` command for list, filter, detail, summary, invalid input, and
rejected mutation options. The portable Linux archive passed the same command
checks, contained no tests or development caches, reproduced byte-for-byte across
builds, and has a published SHA-256 companion.

`omastore lint-manifest .` accepted the root manifest. The prepublication
`omastore check --manifest omastore.toml transientclover-ui/work-box` accepted
the metadata, category, and license; as expected, it could not validate a stable
asset before that release existed. The exact archive, expanded manifest paths,
launcher, checksum, and media paths were validated locally before publication.
