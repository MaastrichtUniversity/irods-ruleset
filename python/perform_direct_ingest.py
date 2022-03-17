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

    source_collection = "/nlmumc/ingest/zones/{}".format(token)
    # dropzone_path = "/nlmumc/ingest/direct/{}".format(token)
    # ctx.callback.msiWriteRodsLog("source_collection {}".format(source_collection), 0)

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(project_id, title, source_collection, "")["arguments"][3]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]
    ingest_resource_host = pre_ingest_results["ingest_resource_host"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    ctx.callback.ingest_collection_data(source_collection, destination_collection, project_id)

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(project_id, collection_id, source_collection, str(difference))

    # # Handle post ingestion operations
    # ctx.callback.post_ingest(project_id, username, token, collection_id, ingest_resource_host, "")
