# Prerequisites for the full test suite
```
icat, ires-hnas-um, ires-hnas-azm, ires-ceph-ac and ires-ceph-gl containers need to be up

keycloak needs to have run

sram-sync needs to have run

epicpid needs to be up (Error-post ingestion)

elasticsearch needs to be up
```
# Prevent pytest cache warnings
```
Make sure the irods user has write access to the test_cases folder (inside ires-hnas-um container)
chmod 777 /rules/test_cases
or
add the argument -p no:cacheprovider
/var/lib/irods/.local/bin/pytest -v -p no:cacheprovider .
```

# How to run all the test cases
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v .
/var/lib/irods/.local/bin/pytest -v -p no:cacheprovider .
```

# How to run all the test cases with print enabled
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v -s -p no:cacheprovider .
```

# How to run a single test file
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py
```
# How to run a single test case
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py::TestDirectIngestUM
```
# How to run a single test
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py::TestDirectIngestUM::test_collection_avu
```

# How to run all the test cases in parallel
```
./rit.sh exec icat
su irods
pip install pytest-xdist
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -p no:cacheprovider -n 3 --dist loadfile -v .
```

# Stop an active ingest

As the iRODS user `rods`, request a stop with the dropzone token and type:

```sh
/rules/tests/run_test.sh -r stop_ingest -a "TOKEN,direct"
/rules/tests/run_test.sh -r stop_ingest -a "TOKEN,mounted"
```

The rule stops the transfer phase, including replica checks and retry waits.
It rejects queued validation, post-ingest work, and dropzones without an active
transfer. Only `rods` can call it; another user with administrator privileges
is also rejected.

The worker checks for requests every second, even when `irsync` is silent.
It terminates its own child process, escalating to a kill after five seconds,
and skips further retries and replica cleanup. Mounted CIFS access is restored
using the normal failure behavior. The ingest failure handler records the stop
reason, sets `error-ingestion`, and submits the usual support request once.
The source and partial destination remain available for restart.

A successful rule return confirms that the transfer and retry loop have exited,
failure handling has finished, and the state is `error-ingestion`. An
acknowledgement timeout after 30 seconds leaves the request pending and reports
an error: **a timeout does not confirm that maintenance can begin**. Blocking
iRODS callbacks can delay both cancellation and the rule's timeout checks. If
completion wins the race, the rule reports that it could not confirm a stop.

Restart later using the existing rule:

```sh
/rules/tests/run_test.sh -r restart_ingest -a "TOKEN,direct"
```

Issue stop/restart commands sequentially for each dropzone. Wait for
`stop_ingest` to confirm completion before restarting. After `restart_ingest`
returns, wait for its delayed transfer to become active before stopping again.
Overlapping administrative commands are not supported. Calling `stop_ingest`
without an active transfer, including calling it again after a successful stop,
returns **No active ingest transfer**.

Coordination uses these single-value dropzone AVUs:

| AVU | Values | Writer |
| --- | --- | --- |
| `ingestTransferState` | `active`, `stopped`, `finished` | Coordinator |
| `ingestStopRequested` | `false`, `true` | Coordinator resets; stop rule requests |
| `ingestWorkerResult` | empty, `stopped`, `exited` | Coordinator resets; worker reports |

Each transfer resets the request and removes the previous worker-result AVU
before becoming active; an absent worker result reads as empty.
`exited` means the worker unwound, including on ordinary failures; it does not
imply successful ingestion. `stopped` coordinator state confirms worker exit,
mounted-access restoration, and completed failure handling with `error-ingestion`.
An ordinary failure or normal completion is never reported as a confirmed stop.
No attempt identifiers, worker hosts, phases, or completed-run history are stored.

If a remote callback fails without evidence of worker exit, the coordinator
retains `active`. Explicit admin restart can override this stale state, so the
admin must first confirm that the old coordinator and worker have exited.
A timeout leaves the stop flag set and does not establish worker exit.

Deploy the coordinator and worker changes together after existing transfers
finish. Workers already running older code cannot use the new protocol. Legacy
run-history AVUs are ignored and need not be removed; `ingestStopRequested` is
reused and reset to `false` when the next transfer starts.

# Restart an ingest after service restart

Before validation, `process_dropzone` checks the dropzone's state and destination.
An unfinished dropzone with a destination is marked `error-ingestion` and left
for an admin to restart; validation and collection creation are skipped.
Completed or removed dropzones are skipped, and `error-post-ingestion` is
preserved for manual finalization repair. Fresh dropzones follow the normal flow.

Run `restart_ingest` explicitly as rods after confirming the old coordinator,
worker, and any `irsync` child have exited. It requires `error-ingestion` and the
recorded project/destination, and resumes copying into that same collection.
It permits stale `ingestTransferState=active` and resets the stop flag and worker
result before copying. There are no worker checks, locks, or automatic recovery
retries: confirming shutdown is the admin's responsibility. Do not overlap
restart commands or restart a still-running ingest.

The old `ingestAttempt`, `ingestWorkerHost`, and `ingestPhase` AVUs are ignored;
they do not need to be removed from existing dropzones. Coordinator and worker
code must be updated together after existing transfers finish because the
internal `perform_irsync` rule no longer takes an attempt argument.

Run the mocked replay, restart, and stop regressions with
`python3 -m pytest -v tests/unit`.

# Stop-ingest tests

The mocked tests need `pytest` and the project's `dh-python-irods-utils`
dependency, but do not start iRODS commands or require server Python modules:

```sh
cd /rules
python3 -m pytest -v tests/unit/test_stop_ingest.py
```

The direct and mounted live test classes share an ordered stop/restart scenario
and are skipped by default. Each creates a project/dropzone, transfers a
2 GiB test file, stops a confirmed running `irsync`, verifies process exit and
worker/coordinator stop acknowledgement, restarts and stops a second transfer,
then restarts again and verifies successful ingestion and checksums. The test
continues immediately after stop confirmation; retry cancellation is covered
by the mocked tests rather than fixed 70-second observation windows.
Normal support-ticket creation is exercised. Use the full-suite prerequisites
above and the `irods` OS account with `rods` iRODS credentials.

Run the direct case on **icat**, where its transfer process and logs are local:

```sh
cd /rules
STOP_INGEST_TEST_TYPE=direct python3 -m pytest -v -s test_cases/test_stop_ingest.py::TestStopDirectIngestUM
```

Run the mounted case on **ires-hnas-um**, with the mounted ingest folder and
resource-server logs available:

```sh
cd /rules
STOP_INGEST_TEST_TYPE=mounted python3 -m pytest -v -s test_cases/test_stop_ingest.py::TestStopMountedIngestUM
```

The test uses `ires-hnas-umResource` / `passRescUM01` and the existing test users.
Set `STOP_INGEST_TEST_BYTES` to a larger byte count if the transfer finishes
before the test observes it. Cleanup retains test data if a stop cannot be
confirmed, so an unresponsive transfer can be inspected safely.

The scenario methods separate preparation, transfer observation, stop checks,
restart verification, and cleanup. Direct ingestion starts as the depositor;
stop and restart run as `rods`. Metadata checks use the existing
`get_collection_attribute_value` rule. The deletion check matches the explicit
`removeDropzone(...)` call in `iqstat -a`. Cleanup retains data while a restart
is still queued or a stop remains unconfirmed.

Reads and coordinator/worker writes use `getCollectionAVU`/`setCollectionAVU`;
worker-result reset uses `remove_collection_attribute_value`, since iRODS
does not accept empty AVU values.
Only the stop flag uses an admin-mode atomic remove-false/add-true operation,
because `rods` may lack a write ACL on a user-started direct dropzone. Process
monitoring uses nonblocking reads so a silent `irsync` can still be stopped;
both silent and continuously emitting workers are covered by the mocked tests.

Validation (2026-09-11): all 41 mocked checks passed, and both live scenarios
passed on their respective development hosts. Each exercised
stop → restart → stop → restart, including both 70-second no-retry windows,
final checksum verification, and deletion scheduling.
