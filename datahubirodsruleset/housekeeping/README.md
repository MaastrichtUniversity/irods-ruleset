# Housekeeping

Run the commands below from `/rules` (the repository root), as the `irods` OS user
with `rods` iRODS credentials. See [package installation](../README.md#installation)
for installing the ruleset.

## Housekeeping report storage

Install the ruleset (`make` in `/rules`) on the catalog provider and resource
servers. On the first `run_housekeeping` call, an absent housekeeping collection
is initialized automatically with report resource `passRescUM01` and retention
of 31 days, before the selected checks run or are queued. The resource must
exist. Authorization, check selection, and execution mode are validated before
initialization.

To choose settings before the first run, or update them later, initialize
explicitly as the `irods` OS user with `rods` iRODS credentials:

```sh
/rules/tests/run_test.sh -r initialize_housekeeping -a "passRescUM01,31" -j
```

This creates `/nlmumc/home/rods/housekeeping` and its `runs` collection. Both
collections are owned by rods, have inheritance disabled, and have other
explicit ACLs removed. It does not change permissions on other parts of the
admin home. Existing runs are preserved. Passing two empty arguments (`-a ","`)
preserves the existing settings, using the defaults on first initialization.

Subsequent `run_housekeeping` calls preserve the existing configuration and
permissions. Missing, duplicate, or invalid settings, and a missing `runs`
collection, produce an error without changing the existing setup. Use
`initialize_housekeeping` explicitly to correct it.

The root collection has single-value `reportResource` and `reportRetentionDays`
AVUs. Re-run initialization to update them. The resource must exist and retention
must be a positive integer. Report writers must explicitly select `reportResource`
when creating data objects (for example `iput -R passRescUM01 ...`). An AVU does
not bind a collection to a resource, and ordinary uploads without resource
selection may use the zone's default resource. Changing this setting does not
move existing replicas.
Collections themselves have no physical resource; their directories appear in
the vault when report data objects are written through iRODS.

Future housekeeping rules should create one immediate child of `runs` per run,
using a unique ID containing letters, numbers, underscores or hyphens. Suggested
contents are `config.json`, `status.json`, `checks/<check>.json`, and `summary.json`.
Run collections must maintain these single-value AVUs for retention:

| AVU | Meaning |
| --- | --- |
| `state` | `queued`, `running`, or terminal `completed`, `partial`, `failed` |
| `finishedAt` | UTC Unix seconds when the run became terminal |

Terminal runs must be immutable; do not reopen them or update their files concurrently with
cleanup. Use a new run ID for another execution. The controller below creates
reports using this structure. Read rules for admin-tools integration are described
below; Airflow scheduling and the admin-tools UI are not implemented yet.

Preview cleanup or run permanent cleanup through the controller:

```sh
/rules/tests/run_test.sh -r cleanup_housekeeping_reports -a "true" -j
/rules/tests/run_test.sh -r run_housekeeping -a "cleanup_reports,async" -j
```

Only immediate run collections finished more than the configured number of days
ago, in a terminal state, and with a valid `finishedAt` timestamp are eligible.
Missing, duplicate or invalid lifecycle metadata, future timestamps, and active
runs are retained. Age comes from `finishedAt`, not directory/file
mtime. Deletion uses iRODS with force enabled and bypasses trash. Each result
lists `eligible`, `deleted`, `skipped` (with reasons), and `errors`; callers must
inspect `errors` for partial deletion failures. No recurring schedule is created;
Airflow can later call this rule daily. Database retention is independent.

Run the isolated retention and authorization tests without an iRODS server:

```sh
python3 -m unittest discover -s tests/unit -p test_housekeeping_reports.py -v
```

After installation, run the live test sequentially as the `irods` OS user with
`rods` credentials on icat:

```sh
cd /rules
python3 -m pytest -v -p no:cacheprovider test_cases/test_housekeeping_reports.py
```

It verifies configured resource placement, authorization, private collection
setup, dry-run behaviour, deletion and retention of temporary test reports.
It skips destructive verification if unrelated reports are already eligible
for cleanup. The initialized root and `runs` collection remain in place.

## Housekeeping controller

Available tasks to schedule with `run_housekeeping`:

| Task | Action |
| --- | --- |
| `required_avus` | Audit required project and collection metadata. |
| `replica_status` | Report non-good project replicas. |
| `physical_files` | Report missing physical copies of project files using `iscan`. |
| `dropzone_consistency` | Compare dropzone directories in iRODS and on disk. |
| `rebalance_resources` | Rebalance replication resources. |
| `cleanup_reports` | Permanently remove expired housekeeping reports. |

Use `run_housekeeping` as the entry point for operational housekeeping. Select
one or more checks joined with `+` in a single argument. This preserves the list
when forwarded through `rit.sh`. Commas in the test launcher separate positional
rule arguments. The second argument is required: `async` or `sync`.

```sh
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "replica_status,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "physical_files,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "dropzone_consistency,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "rebalance_resources,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "cleanup_reports,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus+cleanup_reports,async" -j
# Run synchronously to wait for the results:
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus+cleanup_reports,sync" -j
```

From the host, for example:

```sh
docker exec --user irods dev-icat-1 /rules/tests/run_test.sh -r run_housekeeping -a "required_avus+rebalance_resources,async" -j
```

Space-separated lists remain supported for clients that preserve spaces.

`required_avus` audits metadata. `cleanup_reports` permanently removes eligible
expired reports under the configured retention policy. Only selected
checks run, in the given order; repeated names run once. Empty selections and
unknown names fail before a run is created or any check is executed. Setup and
non-destructive cleanup preview remain available through the utility rules above.

With `async`, the controller creates a `queued` run, writes its configuration and
initial status, submits `execute_housekeeping` to the iRODS delay queue, and
returns the run ID and collection/status/summary paths. It does not execute any
checks in the submitting request. Configuration snapshots the report resource
so changing the global setting cannot move a queued run's later reports.
The worker executes once without automatic retries. Known check failures are
recorded in the report; they do not request a replay of maintenance actions.

Use `sync` for tests or an interactive call that should wait for the results.
It uses the same execution and reporting code, without submitting to the delay
queue. An omitted, empty, or unknown execution mode is rejected.

Poll an asynchronous run using its returned ID:

```sh
/rules/tests/run_test.sh -r get_housekeeping_status -a "RUN_ID" -j
```

Pending runs return their `queued`/`running` state and report paths. Terminal
runs return the full final summary. Polling uses the collection's state AVU
while the worker is active, avoiding reads of a status file being replaced.
The terminal state is published only after the final reports have been closed.
Run IDs and admin authorization are checked on submission, worker execution,
and polling. A worker skips a run that is no longer `queued`; internal worker
calls must not be submitted concurrently for the same run.

The controller owns authorization, one unique run collection, progress,
per-check JSON reports, and finalization. Checks provide their results to the
controller rather than creating separate runs. Adding a check means implementing
its result function and registering it in `CHECKS` in `execute_housekeeping.py`.

The implementation is split by responsibility:

- `run_housekeeping.py`: argument validation and run submission.
- `execute_housekeeping.py`: registered checks, delayed execution, and finalization.
- `reports.py`: status polling, run listing, report reading, and retention cleanup.
- `storage.py`: initialization, configuration validation, and shared storage helpers.

The final summary includes `run_id`, `run_collection`, `summary_path`, submission,
start/end timestamps, run `state`, and a `checks` mapping. Each selected check
has `execution_status`, its `report_path`, and a `summary` or `error`.
`status.json` tracks queued/running/completed/failed checks while the run executes.

A check failure is recorded and later selected checks still run. The run ends
as `completed` if all checks execute successfully, `failed` if all fail, or
`partial` if only some fail. Synchronous failed/partial runs raise an error after
saving the summary. In async mode, admin tools/Airflow must inspect the terminal
state returned by polling and treat `failed`/`partial` as an execution failure;
successful submission alone is not successful housekeeping. Findings about the
environment do not themselves mean execution failed. Queue-submission failures
are recorded as failed runs and raised to the submitter. Storage failures may
prevent finalization and leave a run `queued`/`running`; inspect the delay queue
and server logs for such runs.

## Listing runs and reading task reports

After installing the ruleset, admin tools can use these read-only rules as `rods`:

```sh
# Required arguments: page size (1..100), offset (zero or greater).
/rules/tests/run_test.sh -r list_housekeeping_runs -a "50,0" -j
/rules/tests/run_test.sh -r list_housekeeping_runs -a "50,50" -j
# Existing polling rule: returns the final summary once terminal.
/rules/tests/run_test.sh -r get_housekeeping_status -a "RUN_ID" -j
# Full JSON output for one task in a terminal run.
/rules/tests/run_test.sh -r get_housekeeping_report -a "RUN_ID,required_avus" -j
```

The iRODS signatures are `list_housekeeping_runs(limit, offset, result)` and
`get_housekeeping_report(run_id, check, result)`. Both return JSON in `result`
and reject callers other than `rods`.

The list response contains `runs`, `total`, `limit`, and `offset`. Only immediate
run collections with controller-format IDs are included. Runs are sorted by
catalog creation time descending, with run ID descending as the tie-breaker.
Each entry includes `created_at` (UTC Unix seconds) alongside the same fields
returned by `get_housekeeping_status`: active runs have their overall state and
paths; terminal runs have the final summary, including timestamps, per-task
execution statuses, counts, errors, and report paths. Detailed task outputs are
not loaded by listing. Only the requested page's states and summaries are read;
the immediate-child inventory is enumerated to sort it and calculate `total`.
Offset pages reflect the current inventory, so new runs or retention cleanup can
shift entries between requests. Listing does not provide an atomic snapshot
against concurrent cleanup.

`get_housekeeping_report` returns the complete stored `checks/<check>.json`
document, including findings and captured command output where that task
provides them. It rejects active runs, invalid IDs/names, and checks without a
report in the run's final summary. The check need not still be registered in
the current ruleset, allowing historical reports to remain readable. Object
paths are constructed from validated IDs and names; callers cannot provide an
arbitrary path. Run state and final summaries are used instead of reading a
mutable `status.json` while the worker executes. Missing or unreadable reports
raise an error. Only reports still present under the retention policy are
available.

The admin-tools backend can wrap these rules with `AdminRuleManager`, expose
authenticated list/detail endpoints, and fetch full task output when a user
opens a task. A `completed` execution can still contain audit findings; display
the execution status separately from finding counts.

Run the isolated controller and read-rule tests without an iRODS server:

```sh
python3 -m unittest discover -s tests/unit -p test_housekeeping_avus.py -v
```

## Required AVU audit

Run as rods; storage is initialized automatically on the first run if absent:

```sh
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus,async" -j
```

The rule checks every `P#########` directly under `/nlmumc/projects` and every
immediate `C#########` under those projects. Nested collections are outside its
scope. Collections are enumerated separately from metadata, so entities without
any AVUs are included. Attribute names are fetched in bulk; values, units and
duplicate AVUs are not validated, and project/PC metadata is never repaired.
Projects being created are included. PCs are skipped as unfinished ingests when
all six completion AVU names are absent: `creator`, `depositor`, `PID`,
`latest_version_number`, `schemaName`, and `schemaVersion`. Any one of these
attributes, even with an empty value, makes the PC eligible for the normal audit.
Bare PCs and abandoned ingests therefore also qualify for this heuristic;
dropzone state is not consulted. The report reflects metadata observed during
the run, not a transactionally consistent snapshot.

Required project AVUs:

```text
OBI:0000103 archiveDestinationResource authorizationPeriodEndDate
collectionMetadataSchemas dataRetentionPeriodEndDate dataSteward enableArchive
enableContributorEditMetadata enableDropzoneSharing enableUnarchive ingestResource
latestProjectCollectionNumber resource responsibleCostCenter storageQuotaGb title
```

Required project-collection AVUs:

```text
PID creator dcat:byteSize depositor latest_version_number numFiles schemaName schemaVersion title
```

Each PC also needs at least one `dcat:byteSize_resc_<ID>` / `numFiles_resc_<ID>`
pair with the same numeric resource ID. Multiple pairs are allowed. An unpaired
attribute reports its missing counterpart, even if another complete pair exists.
Resource IDs are matched by their attribute suffix; resource existence is not
validated by this presence check.

The internal AVU check is invoked only through the controller. Its full report
is written to `checks/required_avus.json` within the shared run collection on
`reportResource` (default `passRescUM01`). Read it with
`iget <checks.required_avus.report_path> -`, using the path in the final summary
returned by synchronous execution or status polling. The AVU counts are in
`checks.required_avus.summary`.

The full report contains one finding per affected project/PC, with its path,
entity type and sorted `missing_avus`. PC findings additionally include
`missing_resource_avu_pair`, which is true if no complete numeric pair exists.
The summary counts checked and affected projects/PCs separately. Skipped PCs are
excluded from `project_collections_checked` and counted in
`project_collections_skipped_unfinished_ingest`.
An execution that finds missing metadata is still `completed`. A catalog-query
failure is recorded as a failed check by the controller. Reports are retained
until the backend confirms import and the retention period has elapsed.

Run the mocked checks and the live integration test:

```sh
python3 -m unittest discover -s tests/unit -p 'test_housekeeping*.py' -v
# Sequentially on icat, as the irods OS user with rods credentials:
python3 -m pytest -v -p no:cacheprovider test_cases/test_housekeeping_avus.py
```

Live test cases explicitly select `sync`; isolated unit tests also verify queue
submission, deferred execution, status polling and queue-failure handling with
mocks, without depending on a running delay server.

## Replica-status audit

This check requires `dh-python-irods-utils` v1.2.6, as pinned by the ruleset,
for the `ReplicaStatus` enum. Install the updated dependencies and ruleset on
the rule-engine hosts before using it.

```sh
/rules/tests/run_test.sh -r run_housekeeping -a "replica_status,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "replica_status,sync" -j
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus+replica_status,sync" -j
```

The check scans all replicas of files beneath `/nlmumc/projects/`, including
files directly within that root, nested collections and hidden metadata files.
Every replica whose `DATA_REPL_STATUS` differs from `ReplicaStatus.GOOD.value`
(`'1'`) is a candidate, even when the same file has another good replica.
The complete replica scan finishes before metadata is read in batches for each
distinct enclosing `/nlmumc/projects/P#########/C#########`.

A candidate is skipped if its enclosing project collection has either
`ProcessAttribute.ARCHIVE.value` (`archiveState`) or
`ProcessAttribute.UNARCHIVE.value` (`unArchiveState`). Attribute presence is
sufficient: empty, error and completion values also exclude the candidate.
Otherwise the shared unfinished-ingest heuristic described above applies.
Files outside a standard project collection are reported without these
exclusions. Tape exclusions take precedence over ingest exclusions.

The full report is saved as `checks/replica_status.json`. Each finding has
`path`, `project_collection` (or null), `replica_number`, `replica_status`, and
`resource` (the catalog's leaf resource name). Replica numbers and statuses
remain catalog strings. The summary contains `candidate_replicas`,
`replicas_skipped_tape_operation`, `replicas_skipped_unfinished_ingest`,
`replicas_with_findings`, and `files_with_findings`. The two skip counts and
`replicas_with_findings` sum to `candidate_replicas`.

This audit does not repair replicas or metadata. Findings still produce a
`completed` check; query errors produce a failed check through the controller.
Statuses reflect the scan and exclusions reflect subsequent metadata reads;
the result is not a transactional snapshot.

Run the housekeeping unit suite and the affected live tests sequentially:

```sh
python3 -m unittest discover -s tests/unit -p 'test_housekeeping*.py' -v
python3 -m pytest -v -p no:cacheprovider test_cases/test_housekeeping_avus.py test_cases/test_housekeeping_replica_status.py
```

The live replica test creates temporary files, including stale and locked
replicas and a file with both good and bad replicas. It restores replica
statuses before removing its fixtures and report collections.

## Physical-file audit

Install the updated ruleset using the normal `/rules` Makefile, then queue the
audit or run it synchronously as rods:

```sh
/rules/tests/run_test.sh -r run_housekeeping -a "physical_files,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "physical_files,sync" -j
/rules/tests/run_test.sh -r run_housekeeping -a "replica_status+physical_files,async" -j
```

The check runs `iscan -d -r /nlmumc/projects/` once using the server's existing
iCommands and rods credentials. It includes root-level files, nested collections,
hidden metadata files, unfinished ingests and tape-operation collections. Every
reported missing physical copy is retained, even if the logical file has another
copy. No files or catalog entries are repaired or removed.

The full report is saved as `checks/physical_files.json`. Its `findings` list
contains `path` (logical path), `physical_path`, and `host` for each reported
copy. Only logical paths beneath `/nlmumc/projects/` appear in this list.
The summary contains `missing_physical_copies`, `files_with_findings` (distinct
logical paths), and `errors` (execution diagnostics). The report also preserves
unmodified `stdout`, `stderr`, `return_code` (null if the command could not
start), and an `errors` list. Failed checks include an `error` in the controller's
summary; any findings collected before failure remain available in the report.

Missing-file findings alone produce a `completed` check. A zero command exit
status is accepted, as is the POSIX exit status for `UNIX_FILE_STAT_ERR` with
`ENOENT` (94 on Linux) when accompanied by recognized missing-file messages.
Other exit statuses, unexpected nonblank stdout, or nonblank stderr fail the
check. Later selected checks still execute under the controller's normal failure
handling. Recognized messages outside the project tree are retained only in raw
output and do not contribute to finding counts.

Findings reflect what `iscan` reports, rather than independently verified absence.
The [iRODS 5.1.0 scan implementation](https://github.com/irods/irods/blob/5.1.0/lib/core/src/scanUtil.cpp)
labels filesystem stat errors as missing files, including errors other than
`ENOENT`. Raw output and return codes are retained for investigation. The check
inherits `iscan`'s resource-plugin behavior and observes a changing tree, rather
than a transactional snapshot. No automatic retries or recurring schedule are
added.

Run the housekeeping unit suite locally. After installation, run the live test
sequentially on development icat as the irods OS user with rods credentials:

```sh
python3 -m unittest discover -s tests/unit -p 'test_housekeeping*.py' -v
python3 -m pytest -v -p no:cacheprovider test_cases/test_housekeeping_physical_files.py
```

The live test creates disposable resources and a file with two physical copies,
moves one copy aside, verifies the finding despite the surviving copy, and
restores it before removing its fixtures and report collections. It scans the
whole project tree, so unrelated execution errors can also fail the test.

## Replication-resource rebalance

Queue a rebalance of all replication resources, or run synchronously:

```sh
/rules/tests/run_test.sh -r run_housekeeping -a "rebalance_resources,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "rebalance_resources,sync" -j
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus+rebalance_resources,async" -j
```

The task first fetches the complete list of resources with
`RESC_TYPE_NAME = 'replication'`, ordered by name. It then runs
`iadmin modresc <resource> rebalance` once for each resource, sequentially.
Other resource types are excluded. Resources created after this inventory
snapshot are considered by a later housekeeping run.

Each resource result records its name, execution status and captured command
output. Failed commands also record their error and exit code where available.
Failure on one resource does not prevent attempts on the remaining resources.
Any failure marks the rebalance task as failed; the controller still runs later
selected tasks and publishes the final state using its usual failure handling.
An empty inventory completes successfully with zero counts.

The full report is saved as `checks/rebalance_resources.json`. Its summary
contains `resources_found`, `resources_rebalanced` and `resources_failed`;
its `resources` list contains the individual command results.
Select `async` to queue the rebalance; no automatic retries are added.

Run the isolated command/discovery tests with the other housekeeping unit tests.
The live test uses disposable replication resources and real iCommands, with
its inventory restricted to those test resources:

```sh
python3 -m unittest discover -s tests/unit -p 'test_housekeeping*.py' -v
python3 -m pytest -v -p no:cacheprovider test_cases/test_housekeeping_rebalance.py
```

## Dropzone consistency audit

Install the Python package and native ingest rulebase on iCAT and each
participating resource server using the normal `/rules` Makefile. The check
uses a native `remote(...)` wrapper to return the rods-only Python scanner's
JSON output; both parts must be installed before running it.
On iRODS 5, reload the server configuration (SIGHUP to `irodsServer`) after
installation so the new native wrapper is registered in the rule cache.

```sh
/rules/tests/run_test.sh -r run_housekeeping -a "dropzone_consistency,async" -j
/rules/tests/run_test.sh -r run_housekeeping -a "dropzone_consistency,sync" -j
/rules/tests/run_test.sh -r run_housekeeping -a "required_avus+dropzone_consistency,sync" -j
```

The audit includes all immediate dropzone collections, regardless of state,
under `/nlmumc/ingest/direct` and `/nlmumc/ingest/zones`. Nested collections are
not separate dropzones. The unique resource marked `directIngestResc=true`
provides the staging host and vault path; its directories are
`<vault>/ingest/direct/<token>` and `<vault>/ingest/zones/<token>`.
Mounted dropzones also require `/mnt/ingest/zones/<token>` on the host of their
project's `ingestResource`.

Mounted scan coverage includes all distinct hosts referenced by current
projects, even hosts without any current dropzones. Unreferenced hosts are
outside this audit. Directory scans inspect immediate child directories,
including directory symlinks and names that do not match the usual token
format, without walking their contents. Ordinary files are ignored.

The controller saves `checks/dropzone_consistency.json` with `findings`,
`scans`, `errors`, and a summary of catalog dropzones, successful scan locations,
missing directories, orphan directories, and execution errors. Each scan lists
its host, root, location category (`staging_direct`, `staging_zones`, or
`mounted_data`), type, expected dropzone count, and execution status. Successful
scans also include directory and finding counts.

`missing_on_disk` findings identify each absent expected physical location.
Both physical locations of a mounted dropzone are checked independently.
Findings include token, type, logical/physical paths, host, location category,
available project/state metadata, and `catalog_empty`. An empty catalog
collection can legitimately lack a staging directory until its first file is
written; this remains a finding with `catalog_empty=true`. Data objects in
nested catalog collections make the dropzone nonempty.

`missing_in_irods` findings identify physical directories whose token has no
catalog collection under the corresponding type's parent. A mounted token's
copy on another host does not satisfy its expected host, but is not an orphan
while that token still exists in the mounted catalog inventory.

Findings do not fail execution. Unreachable hosts, missing/unreadable scan
roots, missing/ambiguous staging configuration, and unresolved mounted-host
mappings do fail execution. Independent scans continue and their findings are
preserved; failed inventories never count as empty directories. The controller
uses its normal persisted failure handling and continues later selected checks.

This check performs no cleanup, repair, file-content inspection, or mount-health
diagnosis. It reports observations during the run, without locking dropzone
creation/deletion or applying a grace period; concurrent changes can produce
transient findings.

Run the unit suite and then the live test sequentially as rods on iCAT. The
live test requires project references to both UM and AZM and initialized report
storage. It creates only UUID-prefixed fixtures, verifies remote transport,
both comparison directions, sync/async reports and authorization, then removes
its directories, collections and reports.

```sh
python3 -m unittest discover -s tests/unit -p 'test_housekeeping*.py' -v
python3 -m pytest -v -p no:cacheprovider test_cases/test_housekeeping_dropzones.py
```
