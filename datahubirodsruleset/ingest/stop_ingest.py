# /rules/tests/run_test.sh -r stop_ingest -a "handsome-snake,direct"
import time

from dhpythonirodsutils.enums import DropzoneState

from datahubirodsruleset.utils import TRUE_AS_STRING
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path
from datahubirodsruleset.ingest.ingest_control import get_transfer_state, request_ingest_stop

STOP_TIMEOUT_SECONDS = 30


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def stop_ingest(ctx, token, dropzone_type):
    """As rods, stop the active transfer and wait for completed stop handling.

    Stop/restart commands for a dropzone must be issued sequentially. A timeout
    leaves the request pending and does not confirm that restarting is safe.
    """
    if ctx.callback.get_client_username("")["arguments"][0] != "rods":
        ctx.callback.msiExit("-1", "This rule can only be called by RODS!")

    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    if get_transfer_state(ctx, dropzone_path) != "active":
        ctx.callback.msiExit("-1", f"No active ingest transfer for {dropzone_path}.")

    request_ingest_stop(ctx, dropzone_path)
    ctx.callback.msiWriteRodsLog(f"INFO: Stop requested by rods for {dropzone_path}", 0)

    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while True:
        transfer_state = get_transfer_state(ctx, dropzone_path)
        if transfer_state != "active":
            state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
            if transfer_state == "stopped" and state == DropzoneState.ERROR_INGESTION.value:
                return
            ctx.callback.msiExit("-1", f"Transfer for {dropzone_path} already finished; stop not confirmed.")
        if time.monotonic() >= deadline:
            ctx.callback.msiExit("-1", f"Timed out waiting for {dropzone_path} to stop; request remains pending.")
        time.sleep(1)
