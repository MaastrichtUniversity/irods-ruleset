@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_mounted_ingest(ctx, project_id, title, username, token):
    """
    Perform a mounted (physical directory to logical collection) ingest operation.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project id, ie P00000010
    title: str
        The title of the dropzone / new collection
    username: str
        The username of the person requesting the ingestion
    token: str
        The token of the dropzone to be ingested
    """
    import time

    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(project_id, title, dropzone_path, token, username, "mounted", "")[
            "arguments"
        ][6]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]
    ingest_resource_host = pre_ingest_results["ingest_resource_host"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    # Ingest the files from local directory on resource server to iRODS collection
    try:
        ctx.callback.sync_collection_data(token, destination_collection, username)
    except RuntimeError:
        ctx.callback.setErrorAVU(
            dropzone_path, "state", DropzoneState.ERROR_INGESTION.value, "Error copying ingest zone"
        )

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(project_id, collection_id, dropzone_path, str(difference))

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, username, token, collection_id, ingest_resource_host, "mounted")
