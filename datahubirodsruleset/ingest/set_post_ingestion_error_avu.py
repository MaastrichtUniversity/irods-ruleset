from dhpythonirodsutils.enums import DropzoneState
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2, 3, 4], outputs=[], handler=Output.STORE)
def set_post_ingestion_error_avu(ctx, project_id, collection_id, dropzone_path, message, username):
    """
    Set a post ingestion error AVU close the collection and exit.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project to that the collection that needs to be closed is part of (e.g: P000000010)
    collection_id: str
        The collection that needs to be closed (e.g: C000000002)
    dropzone_path: str
        path to the dropzone (e.g: /nlmumc/ingest/zones/crazy-frog
    message: str
        message to write to rodslog, The reason for the failure. (e.g: "Unable to register PID's for root")
    username: str
        iRODS username
    """
    value = DropzoneState.ERROR_POST_INGESTION.value
    ctx.callback.setCollectionAVU(dropzone_path, "state", value)
    ctx.callback.msiWriteRodsLog("Ingest failed of {} with error status {}".format(dropzone_path, value), 0)
    ctx.callback.msiWriteRodsLog(message, 0)
    ctx.callback.closeProjectCollection(project_id, collection_id)
    # if this go wrong always continue
    try:
        dropzone_token = dropzone_path.split("/")[-1]
        description = (
            'Ingest for dropzone "{}" (Project {}) has failed, we will contact you when we have more information '
            "available".format(dropzone_token, project_id)
        )
        error_message = "{} set to {} because of: {}".format(dropzone_path, value, message)
        ctx.callback.submit_automated_support_request(username, description, error_message)
    finally:
        ctx.callback.msiExit("-1", "{} for {}".format(message, dropzone_path))
