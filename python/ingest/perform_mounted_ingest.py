@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_mounted_ingest(ctx, project_id, title, username, token):
    """
    Perform a direct (collection to collection) ingest operation.

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
    from subprocess import CalledProcessError, check_call  # nosec

    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(project_id, title, dropzone_path, "")["arguments"][3]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]
    ingest_resource_host = pre_ingest_results["ingest_resource_host"]
    destination_resource = pre_ingest_results["destination_resource"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    # Ingest the files from local directory on resource server to iRODS collection
    try:
        ctx.remoteExec(
            ingest_resource_host,
            "",
            "perform_irsync('{}', '{}', '{}', '{}')".format(
                token, destination_collection, destination_resource, username
            ),
            "",
        )
    except RuntimeError:
        ctx.callback.setErrorAVU(
            dropzone_path, "state", DropzoneState.ERROR_INGESTION.value, "Error copying ingest zone"
        )

    pc_instance_path = formatters.format_instance_collection_path(project_id, collection_id)
    pc_schema_path = formatters.format_schema_collection_path(project_id, collection_id)

    try:
        check_call(["ichmod", "own", username, pc_instance_path], shell=False)
        ctx.callback.msiWriteRodsLog("INFO: Updating '{}' ACL was successful".format(pc_instance_path), 0)
        check_call(["ichmod", "own", username, pc_schema_path], shell=False)
        ctx.callback.msiWriteRodsLog("INFO: Updating '{}' ACL was successful".format(pc_schema_path), 0)
    except CalledProcessError:
        ctx.callback.set_post_ingestion_error_avu(
            project_id, collection_id, dropzone_path,
            "Update metadata files ACL failed for '{}'".format(destination_collection)
        )

    dropzone_instance_path = formatters.format_instance_dropzone_path(token, "mounted")
    dropzone_schema_path = formatters.format_schema_dropzone_path(token, "mounted")

    ctx.callback.msiDataObjUnlink('objPath=' + pc_instance_path + '++++forceFlag=', 0)
    ctx.callback.msiDataObjUnlink('objPath=' + pc_schema_path + '++++forceFlag=', 0)

    ctx.callback.msiDataObjCopy(dropzone_instance_path, pc_instance_path, "forceFlag=", 0)
    ctx.callback.msiDataObjCopy(dropzone_schema_path, pc_schema_path, "forceFlag=", 0)

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(project_id, collection_id, dropzone_path, str(difference))

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, username, token, collection_id, ingest_resource_host, "mounted")
