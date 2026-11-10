# Available tasks:
#   required_avus        - Audit required project and collection metadata.
#   replica_status       - Report non-good project replicas.
#   physical_files       - Report missing physical copies of project files.
#   dropzone_consistency - Compare dropzone directories in iRODS and on disk.
#   rebalance_resources  - Rebalance replication resources.
#   cleanup_reports      - Permanently remove expired housekeeping reports.
## Run asynchronously:
# /rules/tests/run_test.sh -r run_housekeeping -a "required_avus,async" -j
## Run synchronously:
# /rules/tests/run_test.sh -r run_housekeeping -a "required_avus,sync" -j
## Execute as rods; join multiple tasks with '+' in one argument:
### Daily run:
# /rules/tests/run_test.sh -r run_housekeeping -a "required_avus+replica_status+physical_files+cleanup_reports,async" -j
### Weekly run:
# /rules/tests/run_test.sh -r run_housekeeping -a "required_avus+replica_status+physical_files+dropzone_consistency+rebalance_resources+cleanup_reports,async" -j
# execute_housekeeping is the internal worker scheduled by run_housekeeping.
"""Validate and submit housekeeping runs for synchronous or delayed execution."""

from datetime import datetime, timezone
import time
import uuid

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.housekeeping.execute_housekeeping import CHECKS, _execute_checks, _finish_run
from datahubirodsruleset.housekeeping.storage import RUNS_COLLECTION, _ensure_housekeeping, _require_rods, _write_report_json


DELAY_OPTIONS = ("<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF>"
                 "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>")


def _selected_checks(checks):
    selected = list(dict.fromkeys(checks.replace("+", " ").split()))
    if not selected:
        raise RuntimeError("Select at least one housekeeping check: " + ", ".join(CHECKS))
    unknown = [name for name in selected if name not in CHECKS]
    if unknown:
        raise RuntimeError("Unknown housekeeping checks: " + ", ".join(unknown)
                           + ". Available checks: " + ", ".join(CHECKS))
    return selected


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def run_housekeeping(ctx, checks, mode):
    """Submit selected checks with an explicit 'async' or 'sync' execution mode."""
    return _submit_housekeeping(ctx, checks, mode)


def _submit_housekeeping(ctx, checks, mode):
    _require_rods(ctx)
    if mode not in ("async", "sync"):
        raise RuntimeError("Execution mode must be 'async' or 'sync'")
    selected = _selected_checks(checks)
    resource = _ensure_housekeeping(ctx)
    submitted = int(time.time())
    run_id = datetime.fromtimestamp(submitted, timezone.utc).strftime("%Y-%m-%d") + "_" + uuid.uuid4().hex
    run_path = RUNS_COLLECTION + "/" + run_id
    ctx.callback.msiCollCreate(run_path, 0, 0)
    ctx.callback.msiCollCreate(run_path + "/checks", 0, 0)
    ctx.callback.setCollectionAVU(run_path, "state", "queued")
    status = {"run_id": run_id, "state": "queued", "submitted_at": submitted,
              "checks": {name: "queued" for name in selected}}
    config = {"checks": selected, "report_resource": resource, "execution_mode": mode}
    _write_report_json(ctx, run_path + "/config.json", resource, config)
    _write_report_json(ctx, run_path + "/status.json", resource, status)
    if mode == "sync":
        summary = _execute_checks(ctx, run_path, config, status)
        if summary["state"] != "completed":
            raise RuntimeError("Housekeeping checks failed; report: " + summary["summary_path"])
        return summary
    try:
        ctx.delayExec(DELAY_OPTIONS, f"execute_housekeeping('{run_id}')", "")
    except Exception as error:
        status.update({"state": "failed", "error": "Could not queue housekeeping: " + str(error)})
        summary = _finish_run(ctx, run_path, resource, status, {})
        raise RuntimeError("Could not queue housekeeping; report: " + summary["summary_path"]) from error
    return dict(status, run_collection=run_path, status_path=run_path + "/status.json",
                summary_path=run_path + "/summary.json")
