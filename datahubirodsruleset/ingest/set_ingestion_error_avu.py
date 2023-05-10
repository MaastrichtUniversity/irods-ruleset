from dhpythonirodsutils.enums import DropzoneState

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def set_ingestion_error_avu(ctx, path, message, project_id, username):
    value = DropzoneState.ERROR_INGESTION.value
    ctx.callback.setCollectionAVU(path, "state", value)
    ctx.callback.msiWriteRodsLog("Ingest failed of {} with error status {}".format(path, value), 0)
    ctx.callback.msiWriteRodsLog(message, 0)
    # if this go wrong always continue
    try:
        ctx.callback.submit_ingest_error_automated_support_request(
            username, project_id, path, "{}: {}".format(value, message)
        )
    finally:
        ctx.callback.msiExit("-1", "{} for {}".format(message, path))
