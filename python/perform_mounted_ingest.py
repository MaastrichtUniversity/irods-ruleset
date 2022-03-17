@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def perform_mounted_ingest(ctx, project_id, title, username, token):
    """
    Perform an ingest

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
    ctx.callback.msiWriteRodsLog("Starting ingestion {}".format(source_collection), 0)
    ctx.callback.setCollectionAVU(source_collection, "state", "ingesting")

    try:
        collection_id = ctx.callback.createProjectCollection(project_id, "", title)["arguments"][1]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("Failed creating projectCollection", 0)
        ctx.callback.setErrorAVU(source_collection, "state", "error-ingestion", "Error creating projectCollection")

    destination_collection = "/nlmumc/projects/{}/{}".format(project_id, collection_id)

    ctx.callback.msiWriteRodsLog("Ingesting {} to {}".format(source_collection, destination_collection), 0)
    ctx.callback.setCollectionAVU(source_collection, "destination", collection_id)

    ingest_resource = ctx.callback.getCollectionAVU(
        "/nlmumc/projects/{}".format(project_id), "ingestResource", "", "", "true"
    )["arguments"][2]

    # Obtain the resource host from the specified ingest resource
    for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
        ingest_resource_host = row[0]

    ctx.callback.msiWriteRodsLog("DEBUG: Resource remote host {}".format(ingest_resource_host), 0)

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

    ctx.callback.msiWriteRodsLog("DEBUG: Done remote", 0)

    after = time.time()
    difference = float(after - before) + 1

    # Calculate and set the byteSize and numFiles AVU. false/false because collection
    # is already open and needs to stay open
    ctx.callback.setCollectionSize(project_id, collection_id, "false", "false")
    num_files = ctx.callback.getCollectionAVU(destination_collection, "numFiles", "", "", "true")["arguments"][2]
    size = ctx.callback.getCollectionAVU(destination_collection, "dcat:byteSize", "", "", "true")["arguments"][2]

    avg_speed = float(size) / 1024 / 1024 / difference
    size_gib = float(size) / 1024 / 1024 / 1024

    ctx.callback.msiWriteRodsLog("{} : Ingested {} GiB in {} files".format(source_collection, size_gib, num_files), 0)
    ctx.callback.msiWriteRodsLog("{} : Sync took {} seconds".format(source_collection, difference), 0)
    ctx.callback.msiWriteRodsLog("{} : AVG speed was {} MiB/s".format(source_collection, avg_speed), 0)

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, username, token, collection_id, ingest_resource_host, "mounted")
