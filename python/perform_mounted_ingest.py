@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_mounted_ingest(ctx, project_id, title, username, token):
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

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(ctx, project_id, title, source_collection, "")["arguments"][3]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]
    ingest_resource_host = pre_ingest_results["ingest_resource_host"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    # Ingest the files from local directory on resource server to iRODS collection
    try:
        ctx.remoteExec(
            ingest_resource_host,
            "",
            "msiput_dataobj_or_coll('/mnt/ingest/zones/{}', 'dummy_resource', 'numThreads=10++++forceFlag=', {}, '')".format(
                token, destination_collection
            ),
            "",
        )
    except RuntimeError:
        ctx.callback.setErrorAVU(source_collection, "state", "error-ingestion", "Error copying ingest zone")

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(ctx, project_id, collection_id, source_collection, difference)

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, username, token, collection_id, ingest_resource_host, "mounted")
