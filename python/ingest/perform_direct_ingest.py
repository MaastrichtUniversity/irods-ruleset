@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_direct_ingest(ctx, project_id, title, username, token):
    """
    Perform a direct (collection to collection) ingest operation.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The project id, ie P00000010
    title: str
        The title of the dropzone / new collection
    username: str
        The username of the person requesting the ingest
    token: str
        The token of the dropzone to be ingested
    """
    import time

    dropzone_path = "/nlmumc/ingest/direct/{}".format(token)

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(project_id, title, dropzone_path, "")["arguments"][3]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]
    ingest_resource_host = pre_ingest_results["ingest_resource_host"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    retry_counter = 5
    status = 0
    while retry_counter > 0:
        ret = ctx.callback.ingest_collection_data(dropzone_path, destination_collection, project_id, "")
        status = int(ret["arguments"][3])
        if status != 0:
            retry_counter -= 1
            ctx.callback.msiWriteRodsLog("DEBUG: Decrement retry_counter: {}".format(str(retry_counter)), 0)
        else:
            retry_counter = 0
            ctx.callback.msiWriteRodsLog("INFO: Ingest collection data '{}' was successful".format(dropzone_path), 0)
        time.sleep(10)

    if status != 0:
        ctx.callback.setErrorAVU(dropzone_path, "state", "error-ingestion", "Error copying ingest zone")

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(project_id, collection_id, dropzone_path, str(difference))

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, username, token, collection_id, ingest_resource_host, "direct")
