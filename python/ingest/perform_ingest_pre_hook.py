@make(inputs=[0, 1, 2, 3, 4, 5], outputs=[6], handler=Output.STORE)
def perform_ingest_pre_hook(ctx, project_id, title, dropzone_path, token, depositor, dropzone_type):
    """
    This rule is part the ingestion workflow.
    Perform the preliminary common tasks for both 'mounted' and 'direct' ingest.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project id, ie P00000010
    title: str
        The title of the dropzone / new collection
    dropzone_path: str
        The dropzone absolute path

    Returns
    -------
    dict
        collection_id, destination_collection & ingest_resource_host
    """
    ctx.callback.msiWriteRodsLog("Starting ingestion {}".format(dropzone_path), 0)
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)

    try:
        collection_id = ctx.callback.createProjectCollection(project_id, "", title)["arguments"][1]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("Failed creating projectCollection", 0)
        ctx.callback.setErrorAVU(
            dropzone_path, "state", DropzoneState.ERROR_INGESTION.value, "Error creating projectCollection"
        )

    destination_project_collection_path = format_project_collection_path(ctx, project_id, collection_id)

    ctx.callback.msiWriteRodsLog("Ingesting {} to {}".format(dropzone_path, destination_project_collection_path), 0)
    ctx.callback.setCollectionAVU(dropzone_path, "destination", collection_id)

    ingest_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]
    # Obtain the resource host from the specified ingest resource
    for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
        ingest_resource_host = row[0]

    ctx.callback.msiWriteRodsLog("DEBUG: Resource remote host {}".format(ingest_resource_host), 0)

    try:
        ctx.remoteExec(
            ingest_resource_host,
            "",
            "save_dropzone_pre_ingest_info('{}', '{}', '{}', '{}')".format(
                token, collection_id, depositor, dropzone_type
            ),
            "",
        )
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("Failed creating dropzone pre-ingest information", 0)
        ctx.callback.setErrorAVU(
            dropzone_path,
            "state",
            DropzoneState.ERROR_INGESTION.value,
            "Failed creating dropzone pre-ingest information",
        )

    ctx.callback.msiWriteRodsLog(
        "DEBUG: dropzone pre-ingest information created on {} for {}".format(ingest_resource_host, token), 0
    )

    return {
        "collection_id": collection_id,
        "destination_collection": destination_project_collection_path,
        "ingest_resource_host": ingest_resource_host,
    }
