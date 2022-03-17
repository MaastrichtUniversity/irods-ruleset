@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def perform_ingest_pre_hook(ctx, project_id, title, dropzone_path):
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
    dropzone_path: str
        The dropzone absolute path
    """
    ctx.callback.msiWriteRodsLog("Starting ingestion {}".format(dropzone_path), 0)
    ctx.callback.setCollectionAVU(dropzone_path, "state", "ingesting")

    try:
        collection_id = ctx.callback.createProjectCollection(project_id, "", title)["arguments"][1]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("Failed creating projectCollection", 0)
        ctx.callback.setErrorAVU(dropzone_path, "state", "error-ingestion", "Error creating projectCollection")

    destination_collection = "/nlmumc/projects/{}/{}".format(project_id, collection_id)

    ctx.callback.msiWriteRodsLog("Ingesting {} to {}".format(dropzone_path, destination_collection), 0)
    ctx.callback.setCollectionAVU(dropzone_path, "destination", collection_id)

    ingest_resource = ctx.callback.getCollectionAVU(
        "/nlmumc/projects/{}".format(project_id), "ingestResource", "", "", "true"
    )["arguments"][2]

    # Obtain the resource host from the specified ingest resource
    for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
        ingest_resource_host = row[0]

    ctx.callback.msiWriteRodsLog("DEBUG: Resource remote host {}".format(ingest_resource_host), 0)

    return {
        "collection_id": collection_id,
        "destination_collection": destination_collection,
        "ingest_resource_host": ingest_resource_host,
    }
