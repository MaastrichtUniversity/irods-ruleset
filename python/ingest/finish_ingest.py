@make(inputs=[0, 1, 2, 3, 4, 5], outputs=[], handler=Output.STORE)
def finish_ingest(ctx, project_id, username, token, collection_id, ingest_resource_host, dropzone_type):
    """
    Actions to be performed after an ingest is completed
        Setting AVUs
        Removing AVUs
        Requesting PID's for root collection
        Updating the instance.json and schema.json
        Create metadata_versions folder with copy of schema and instance
        Requesting PID's for version 1 of collection,schema and metadata
        Recalculate collection size
        Removing the dropzone
        Closing the project collection

    If this rules execution stop prematurely and the drop-zone state AVU is "error-post-ingestion", it is safe
    to re-run the rule to perform the post-ingest actions.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The token of the dropzone to be ingested
    project_id: str
        The project id, ie P00000010
    collection_id: str
        The collection id, ie C00000004
    username: str
        The username of the person requesting the ingest
    ingest_resource_host: str
        The remote host that was ingested to, ie 'ires-dh.local
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'
    """
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)

    destination_collection = "/nlmumc/projects/{}/{}".format(project_id, collection_id)
    # Set the Creator AVU
    ctx.callback.msiWriteRodsLog("{} : Setting AVUs to {}".format(dropzone_path, destination_collection), 0)
    # fatal = "false", because we want to raise the exception with set_post_ingestion_error_avu.
    # This allows to update the state AVU to 'error-post-ingestion'
    ret = ctx.get_user_attribute_value(username, "email", "false", "result")["arguments"][3]
    email = json.loads(ret)["value"]
    if email == "":
        ctx.callback.set_post_ingestion_error_avu(
            project_id, collection_id, dropzone_path, "User '{}' doesn't have an email AVU".format(username)
        )
    ctx.callback.setCollectionAVU(destination_collection, "creator", email)

    # Requesting a PID via epicPID for version 0 (root version)
    handle_pids = ctx.callback.get_versioned_pids(project_id, collection_id, "", "")["arguments"][3]
    handle_pids = json.loads(handle_pids)

    if "collection" in handle_pids and handle_pids["collection"]["handle"] != "":
        # Setting the PID as AVU on the project collection
        ctx.callback.setCollectionAVU(destination_collection, "PID", handle_pids["collection"]["handle"])
    else:
        ctx.callback.set_post_ingestion_error_avu(
            project_id, collection_id, dropzone_path, "Unable to register PID's for root"
        )

    # Requesting PID's for Project Collection version 1 (includes instance and schema)
    ctx.callback.get_versioned_pids(project_id, collection_id, "1", "")

    try:
        # Fill the instance.json and schema.json with the information needed in that instance (ie. handle PID) and schema version 1
        ctx.callback.update_metadata_during_ingest(project_id, collection_id, handle_pids["collection"]["handle"], "1")
    except KeyError:
        ctx.callback.set_post_ingestion_error_avu(project_id, collection_id, dropzone_path, "Failed to update instance")
    except RuntimeError:
        ctx.callback.set_post_ingestion_error_avu(project_id, collection_id, dropzone_path, "Failed to update instance")

    # Query drop-zone state AVU and create 'overwrite flag' variable to copy the metadata json files
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", "true")["arguments"][2]
    overwrite_flag = "false"
    if state == "error-post-ingestion":
        overwrite_flag = "true"
    # Create metadata_versions and copy schema and instance from root to that folder as version 1
    ctx.callback.create_ingest_metadata_snapshot(project_id, collection_id, dropzone_path, overwrite_flag)

    # Set latest version number to 1 for metadata latest version
    ctx.callback.setCollectionAVU(destination_collection, "latest_version_number", "1")

    # Calculate and set the byteSize and numFiles AVU. false/false because collection
    # is already open and needs to stay open.
    # Recalculation is required because we copied files and created a folder
    ctx.callback.setCollectionSize(project_id, collection_id, "false", "false")

    # Copy schemaVersion and schemaName AVU from dropzone to the ingested collection
    schema_name = ctx.callback.getCollectionAVU(dropzone_path, "schemaName", "", "", "true")["arguments"][2]
    schema_version = ctx.callback.getCollectionAVU(dropzone_path, "schemaVersion", "", "", "true")["arguments"][2]
    ctx.callback.setCollectionAVU(destination_collection, "schemaName", schema_name)
    ctx.callback.setCollectionAVU(destination_collection, "schemaVersion", schema_version)

    # Setting the State AVU to Ingested
    ctx.callback.setCollectionAVU(dropzone_path, "state", "ingested")

    # Remove the temporary sizeIngested AVU at *dstColl
    ctx.callback.remove_size_ingested_avu(destination_collection)

    # Close collection by making all access read only
    ctx.callback.closeProjectCollection(project_id, collection_id)

    if dropzone_type == "mounted":
        # The unmounting of the physical mount point is not done in the delay() where msiRmColl on the token is done.
        # This is because of a bug in the unmount. This is kept in memory for
        # the remaining of the irodsagent session.
        # See also: https://groups.google.com/d/msg/irod-chat/rasDT-AGAVQ/Bb31VJ9SAgAJ
        try:
            ctx.callback.msiPhyPathReg(dropzone_path, "", "", "unmount", 0)
        except RuntimeError:
            ctx.callback.setErrorAVU(dropzone_path, "state", "error-post-ingestion", "Error unmounting")

    ctx.callback.delayRemoveDropzone(dropzone_path, ingest_resource_host, token, dropzone_type)
    ctx.callback.msiWriteRodsLog("Finished ingesting {} to {}".format(dropzone_path, destination_collection), 0)