@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def create_collection_metadata_snapshot(ctx, project_id, collection_id):
    """
    Create a snapshot of the collection metadata files (schema & instance):
        * Check user edit metadata permission
        * Check if the snapshot folder (.metadata_versions) already exists, if not create it
        * Request the new versions handle PIDs
        * Update instance.json and schema.json properties
        * Copy the current metadata files to .metadata_versions and add the version number in the filename
        * Increment the AVU latest_version_number

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (ie. P000000010)
    collection_id : str
        The collection where the instance.json is to fill (ie. C000000002)
    """
    collection_path = "/nlmumc/projects/{}/{}".format(project_id, collection_id)
    project_path = "/nlmumc/projects/{}".format(project_id)
    metadata_folder_path = collection_path + "/.metadata_versions"
    metadata_folder_exist = True

    # Check if user is allowed to edit metadata for this project
    can_edit_metadata = ctx.callback.check_edit_metadata_permission(project_path, "")["arguments"][1]
    if can_edit_metadata == "false":
        ctx.callback.msiExit("-1", "ERROR: User has no edit metadata rights for  '{}'".format(project_id))

    # Check .metadata_versions folder exists
    try:
        ctx.callback.msiObjStat(metadata_folder_path, irods_types.RodsObjStat())
    except RuntimeError:
        metadata_folder_exist = False

    if not metadata_folder_exist:
        try:
            ctx.callback.msiCollCreate(metadata_folder_path, 0, 0)
            ctx.callback.msiWriteRodsLog("DEBUG: '{}' created".format(metadata_folder_path), 0)
        except RuntimeError:
            ctx.callback.msiExit("-1", "ERROR: Couldn't create '{}'".format(metadata_folder_path))

    source_schema = collection_path + "/schema.json"
    source_instance = collection_path + "/instance.json"

    version = ctx.callback.getCollectionAVU(collection_path, "latest_version_number", "", "", "false")["arguments"][2]
    new_version = 0
    try:
        version_number = int(version)
        new_version = version_number + 1
    except ValueError:
        ctx.callback.msiExit(
            "-1", "ERROR: 'Cannot increment version number '{}' for collection '{}'".format(version, collection_path)
        )

    destination_schema = metadata_folder_path + "/schema.{}.json".format(new_version)
    destination_instance = metadata_folder_path + "/instance.{}.json".format(new_version)

    # Request new PIDs
    handle_pids_version = ctx.callback.get_versioned_pids(project_id, collection_id, str(new_version), "")["arguments"][
        3
    ]
    handle_pids_version = json.loads(handle_pids_version)
    if not handle_pids_version:
        ctx.callback.msiExit(
            "-1", "Retrieving multiple PID's failed for {} version {}".format(collection_path, new_version)
        )

    # Overwriting the schema:isBasedOn with the PID for schema version
    handle = handle_pids_version["collection"]["handle"].rsplit(".", 1)[0]
    schema_url = "https://hdl.handle.net/{}{}.{}".format(handle, "schema", new_version)
    try:
        ctx.callback.update_metadata_during_edit_collection(collection_path, schema_url, handle_pids_version["collection"]["handle"])
    except RuntimeError:
        ctx.callback.msiExit("-1", "ERROR: Couldn't update the instance snapshot '{}'".format(destination_instance))

    # Copy current metadata json files to /.metadata_versions
    try:
        ctx.callback.msiDataObjCopy(source_schema, destination_schema, "", 0)
        ctx.callback.msiDataObjCopy(source_instance, destination_instance, "", 0)
    except RuntimeError:
        ctx.callback.msiExit("-1", "ERROR: Couldn't create the metadata snapshots '{}'".format(metadata_folder_path))

    # Only set latest_version_number if everything went fine.
    ctx.callback.setCollectionAVU(collection_path, "latest_version_number", str(new_version))
