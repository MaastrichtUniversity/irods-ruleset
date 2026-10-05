"""Validate in the delay queue before deciding whether maintenance postpones ingest."""

import time

from dhpythonirodsutils.enums import DropzoneState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.ingest.maintenance import lead_seconds, parse_window
from datahubirodsruleset.ingest.process_dropzone import ingest, stop_ingestion, validate
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1, 2, 3, 4], outputs=[], handler=Output.STORE)
def schedule_maintenance_ingest(ctx, token, depositor, dropzone_type, start, end):
    """Run the expensive preflight asynchronously; defer only eligible ingests."""
    start, end = parse_window(start, end)
    validation_results, dropzone_path = validate(ctx, token, depositor, dropzone_type)
    if validation_results["validation_errors"]:
        return stop_ingestion(ctx, dropzone_path, validation_results["validation_errors"])

    size = int(ctx.callback.getCollectionAVU(
        dropzone_path, "totalSize", "", "", TRUE_AS_STRING
    )["arguments"][2])
    now = int(time.time())
    if now >= end or now < start - lead_seconds(size):
        return ingest(ctx, dropzone_path, validation_results["project_id"], depositor, token, dropzone_type)

    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.IN_QUEUE_FOR_VALIDATION.value)
    ctx.delayExec(
        f"<PLUSET>{end - now}s</PLUSET><EF>30s REPEAT 0 TIMES</EF><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        f"process_dropzone('{token}', '{depositor}', '{dropzone_type}')",
        "",
    )
