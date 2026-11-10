"""Execute selected housekeeping checks and persist their progress and results."""

import json
import time

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.housekeeping.check_required_avus import _audit_required_avus
from datahubirodsruleset.housekeeping.check_replica_status import _audit_replica_status
from datahubirodsruleset.housekeeping.check_physical_files import _audit_physical_files
from datahubirodsruleset.housekeeping.check_dropzone_consistency import _audit_dropzone_consistency
from datahubirodsruleset.housekeeping.rebalance_resources import _rebalance_resources
from datahubirodsruleset.housekeeping.reports import _cleanup_housekeeping_reports
from datahubirodsruleset.housekeeping.storage import _metadata, _require_rods, _run_path, _write_report_json
from datahubirodsruleset.utils import read_data_object_from_irods


def _cleanup_reports(ctx):
    result = _cleanup_housekeeping_reports(ctx, "false")
    return {"check": "cleanup_reports", "execution_status": "failed" if result["errors"] else "completed",
            "summary": {"deleted": len(result["deleted"]), "skipped": len(result["skipped"]),
                        "errors": len(result["errors"])}, "details": result}


CHECKS = {"required_avus": _audit_required_avus, "replica_status": _audit_replica_status,
          "physical_files": _audit_physical_files,
          "dropzone_consistency": _audit_dropzone_consistency,
          "rebalance_resources": _rebalance_resources,
          "cleanup_reports": _cleanup_reports}


@make(inputs=[0], outputs=[], handler=Output.STORE)
def execute_housekeeping(ctx, run_id):
    """Internal one-shot delay-queue worker; completed/running runs are not replayed."""
    _require_rods(ctx)
    run_path = _run_path(run_id)
    if _metadata(ctx, run_path).get("state") != "queued":
        return
    config = json.loads(read_data_object_from_irods(ctx, run_path + "/config.json"))
    status = json.loads(read_data_object_from_irods(ctx, run_path + "/status.json"))
    _execute_checks(ctx, run_path, config, status)


def _execute_checks(ctx, run_path, config, status):
    resource = config["report_resource"]
    selected = config["checks"]
    status.update({"state": "running", "started_at": int(time.time())})
    ctx.callback.setCollectionAVU(run_path, "state", "running")
    _write_report_json(ctx, run_path + "/status.json", resource, status)

    results = {}
    failures = []
    for name in selected:
        status["checks"][name] = "running"
        _write_report_json(ctx, run_path + "/status.json", resource, status)
        try:
            report = CHECKS[name](ctx)
        except Exception as error:
            report = {"check": name, "execution_status": "failed", "error": str(error)}
        report_path = run_path + f"/checks/{name}.json"
        _write_report_json(ctx, report_path, resource, report)
        status["checks"][name] = report["execution_status"]
        results[name] = {key: value for key, value in report.items() if key in ("execution_status", "summary", "error")}
        results[name]["report_path"] = report_path
        if report["execution_status"] == "failed":
            failures.append(name)
        _write_report_json(ctx, run_path + "/status.json", resource, status)

    state = "completed" if not failures else "failed" if len(failures) == len(selected) else "partial"
    status["state"] = state
    return _finish_run(ctx, run_path, resource, status, results)


def _finish_run(ctx, run_path, resource, status, results):
    status["finished_at"] = int(time.time())
    summary = dict(status, checks=results, run_collection=run_path, summary_path=run_path + "/summary.json")
    _write_report_json(ctx, summary["summary_path"], resource, summary)
    _write_report_json(ctx, run_path + "/status.json", resource, status)
    ctx.callback.setCollectionAVU(run_path, "finishedAt", str(status["finished_at"]))
    ctx.callback.setCollectionAVU(run_path, "state", status["state"])
    return summary
