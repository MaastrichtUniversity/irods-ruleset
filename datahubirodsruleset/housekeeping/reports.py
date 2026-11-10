# Execute as rods:
# /rules/tests/run_test.sh -r get_housekeeping_status -a "RUN_ID" -j
# /rules/tests/run_test.sh -r list_housekeeping_runs -a "50,0" -j
# /rules/tests/run_test.sh -r get_housekeeping_report -a "RUN_ID,required_avus" -j
# /rules/tests/run_test.sh -r cleanup_housekeeping_reports -a "true" -j   # preview
# /rules/tests/run_test.sh -r run_housekeeping -a "cleanup_reports,async" -j
"""Read housekeeping progress and reports, and remove expired runs."""

import json
import re
import time

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import query_value
from datahubirodsruleset.housekeeping.storage import (
    REPORT_COLLECTION, RUNS_COLLECTION, TERMINAL_STATES, _metadata, _positive_integer,
    _require_rods, _run_path,
)
from datahubirodsruleset.utils import read_data_object_from_irods


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_housekeeping_status(ctx, run_id):
    """Return queued/running state, or the immutable final summary for a terminal run."""
    _require_rods(ctx)
    return _read_run_status(ctx, run_id)


def _read_run_status(ctx, run_id):
    run_path = _run_path(run_id)
    state = _metadata(ctx, run_path).get("state")
    if not state:
        raise RuntimeError("Housekeeping run does not exist or has no state")
    if state in TERMINAL_STATES:
        return json.loads(read_data_object_from_irods(ctx, run_path + "/summary.json"))
    # Do not read status.json while the worker may be replacing it. The terminal
    # state AVU is published only after the final summary has been closed.
    return {"run_id": run_id, "state": state, "run_collection": run_path,
            "status_path": run_path + "/status.json", "summary_path": run_path + "/summary.json"}


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def list_housekeeping_runs(ctx, limit, offset):
    """List retained runs by catalog creation time, newest first (limit 1..100)."""
    _require_rods(ctx)
    if not re.fullmatch(r"[0-9]+", str(limit)) or not 1 <= int(limit) <= 100:
        raise RuntimeError("limit must be an integer between 1 and 100")
    if not re.fullmatch(r"[0-9]+", str(offset)):
        raise RuntimeError("offset must be a non-negative integer")
    limit, offset = int(limit), int(offset)
    candidates = []
    for path, created_at in row_iterator(
        "COLL_NAME, COLL_CREATE_TIME", f"COLL_PARENT_NAME = {query_value(RUNS_COLLECTION)}",
        AS_LIST, ctx.callback,
    ):
        run_id = path[len(RUNS_COLLECTION) + 1:]
        try:
            if _run_path(run_id) != path:
                continue
        except RuntimeError:
            continue
        candidates.append((int(created_at), run_id))
    candidates.sort(reverse=True)
    runs = [dict(_read_run_status(ctx, run_id), created_at=created_at)
            for created_at, run_id in candidates[offset:offset + limit]]
    return {"runs": runs, "total": len(candidates), "limit": limit, "offset": offset}


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_housekeeping_report(ctx, run_id, check):
    """Read a selected check's full report after its run becomes terminal."""
    _require_rods(ctx)
    run_path = _run_path(run_id)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", check):
        raise RuntimeError("Invalid housekeeping check name")
    summary = _read_run_status(ctx, run_id)
    if summary["state"] not in TERMINAL_STATES:
        raise RuntimeError("Housekeeping reports are only available for terminal runs")
    if check not in summary["checks"]:
        raise RuntimeError("Check has no report in this housekeeping run")
    return json.loads(read_data_object_from_irods(ctx, run_path + f"/checks/{check}.json"))


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def cleanup_housekeeping_reports(ctx, dry_run):
    """Permanently remove expired terminal runs based on completion time.

    Run collections use single-value state and finishedAt AVUs;
    the timestamp is UTC Unix seconds. No timestamp is inferred from file mtime.
    Pass 'true' to preview or 'false' to delete. Never call concurrently with
    lifecycle updates to an existing terminal run.
    """
    return _cleanup_housekeeping_reports(ctx, dry_run)


def _cleanup_housekeeping_reports(ctx, dry_run):
    _require_rods(ctx)
    if dry_run not in ("true", "false"):
        raise RuntimeError("dry_run must be 'true' or 'false'")
    try:
        days = _positive_integer(_metadata(ctx, REPORT_COLLECTION).get("reportRetentionDays"))
    except ValueError as error:
        raise RuntimeError("Initialize housekeeping with a valid reportRetentionDays before cleanup") from error
    now = int(time.time())
    cutoff = now - days * 86400
    result = {"dry_run": dry_run == "true", "retention_days": days,
              "eligible": [], "deleted": [], "skipped": [], "errors": []}
    # Materialize before deleting, so catalog pagination cannot skip later runs.
    paths = [row[0] for row in row_iterator(
        "COLL_NAME", f"COLL_PARENT_NAME = {query_value(RUNS_COLLECTION)}", AS_LIST, ctx.callback
    )]
    for path in paths:
        parent, _, name = path.rpartition("/")
        if parent != RUNS_COLLECTION or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
            result["skipped"].append({"path": path, "reason": "Unexpected run path"})
            continue
        metadata = _metadata(ctx, path)
        reason = None
        if metadata.get("state") not in TERMINAL_STATES:
            reason = "Run is not in an unambiguous terminal state"
        else:
            try:
                finished = _positive_integer(metadata.get("finishedAt"))
            except ValueError:
                reason = "Missing, invalid or ambiguous finishedAt timestamp"
            else:
                if finished > now:
                    reason = "finishedAt timestamp is in the future"
                elif finished >= cutoff:
                    reason = "Within retention period"
        if reason:
            result["skipped"].append({"path": path, "reason": reason})
            continue
        result["eligible"].append(path)
        if dry_run == "false":
            try:
                ctx.callback.msiRmColl(path, "forceFlag=", 0)
            except RuntimeError as error:
                result["errors"].append({"path": path, "error": str(error)})
                continue
            result["deleted"].append(path)
            ctx.callback.msiWriteRodsLog(f"INFO: Permanently removed expired housekeeping run '{path}'", 0)
    return result
