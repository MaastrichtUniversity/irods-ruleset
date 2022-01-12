@make(inputs=[0, 1, 2, 3, 4], outputs=[], handler=Output.STORE)
def post_ingest(ctx, project_id, username, token, collection_id, ingest_resource_host):
    """
    Actions to be performed after an ingest is completed
        Setting AVUs
        Removing AVUs
        Requesting a PID
        Removing the dropzone
        Updating the instance.json
        Closing the project collection

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
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
    """
    destination_collection = "/nlmumc/projects/{}/{}".format(project_id, collection_id)
    source_collection = "/nlmumc/ingest/zones/{}".format(token)

    # Set the Creator AVU
    ctx.callback.msiWriteRodsLog("{} : Setting AVUs to {}".format(source_collection, destination_collection), 0)
    email = username
    for row in row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'email'".format(username),
        AS_LIST,
        ctx.callback,
    ):
        email = row[0]
    ctx.callback.setCollectionAVU(destination_collection, "creator", email)

    # Requesting a PID via epicPID for version 0 (root version)
    handle_pid = ctx.callback.get_versioned_pids(project_id, collection_id, "0", "")["arguments"][3]
    if handle_pid == "":
        ctx.callback.msiWriteRodsLog("Retrieving PID failed for {}, leaving blank".format(destination_collection), 0)
    else:
        # Setting the PID as AVU on the project collection
        ctx.callback.setCollectionAVU(destination_collection, "PID", handle_pid)

    # Fill the instance.json with the information needed in that instance (ie. handle PID) version 1
    ctx.callback.update_instance(project_id, collection_id, handle_pid, "1")

    # Create metadata_versions and copy schema and instance from root to that folder as version 1
    ctx.callback.create_ingest_metadata_versions(project_id, collection_id)

    # Requesting PID's for Project Collection version 1 (includes instance and schema)
    ctx.callback.get_versioned_pids(project_id, collection_id, "1", "")

    # Set latest version number to 1 for metadata latest version
    ctx.callback.setCollectionAVU(destination_collection, "latest_version_number", "1")

    # Calculate and set the byteSize and numFiles AVU. false/false because collection
    # is already open and needs to stay open.
    # Recalculation is required because we copied files and created a folder
    ctx.callback.setCollectionSize(project_id, collection_id, "false", "false")

    # Copy schemaVersion and schemaName AVU from dropzone to the ingested collection
    schemaName = ctx.callback.getCollectionAVU(source_collection, "schemaName", "", "", "true")["arguments"][2]
    schemaVersion = ctx.callback.getCollectionAVU(source_collection, "schemaVersion", "", "", "true")["arguments"][2]
    ctx.callback.setCollectionAVU(destination_collection, "schemaName", schemaName)
    ctx.callback.setCollectionAVU(destination_collection, "schemaVersion", schemaVersion)

    # Setting the State AVU to Ingested
    ctx.callback.msiWriteRodsLog("Finished ingesting {} to {}".format(source_collection, destination_collection), 0)
    ctx.callback.setCollectionAVU(source_collection, "state", "ingested")

    # Remove the temporary sizeIngested AVU at *dstColl
    ctx.callback.remove_size_ingested_avu(destination_collection)

    # Close collection by making all access read only
    ctx.callback.closeProjectCollection(project_id, collection_id)

    # The unmounting of the physical mount point is not done in the delay() where msiRmColl on the token is done.
    # This is because of a bug in the unmount. This is kept in memory for
    # the remaining of the irodsagent session.
    # See also: https://groups.google.com/d/msg/irod-chat/rasDT-AGAVQ/Bb31VJ9SAgAJ
    try:
        ctx.callback.msiPhyPathReg(source_collection, "", "", "unmount", 0)
    except RuntimeError:
        ctx.callback.setErrorAVU(source_collection, "state", "error-post-ingestion", "Error unmounting")

    # Get environment config option for setting the delay for drop zone removal
    ingest_remove_delay = ctx.callback.msi_getenv("IRODS_INGEST_REMOVE_DELAY", "")["arguments"][1]

    ctx.callback.delayRemoveDropzone(ingest_remove_delay, source_collection, ingest_resource_host, token)
