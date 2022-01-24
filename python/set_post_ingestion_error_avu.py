@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def set_post_ingestion_error_avu(ctx, project_id, collection_id, dropzone, message):
    """
    Set a post ingestion error AVU close the collection and exit.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The project to that the collection that needs to be closed is part of (ie. P000000010)
    collection_id: str
        The collection that needs to be closed (ie. C000000002)
    dropzone: str
        path to the dropzone (ie. /nlmumc/ingest/zones/crazy-frog
    message: str
        message to write to rodslog, The reason for the failure. (ie. "Unable to register PID's for root")
    """

    value = "error-post-ingestion"
    ctx.callback.setCollectionAVU(dropzone, "state", value)
    ctx.callback.msiWriteRodsLog("Ingest failed of {} with error status {}".format(dropzone, value), 0)
    ctx.callback.msiWriteRodsLog(message, 0)
    ctx.callback.closeProjectCollection(project_id, collection_id)
    ctx.callback.msiExit("-1", "{} for {}".format(message, dropzone))
