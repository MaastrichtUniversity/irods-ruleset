@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def create_collection_metadata_snapshot(ctx, project_id, collection_id):
    """
    Create a snapshot of the collection metadata files (schema & instance):
        * Check if the snapshot folder (.metadata_versions) already exists, if not create it
        * Copy the current metadata files to .metadata_versions and add a timestamp in the filename
        * Call update_instance_snapshot to update the schema:isBasedOn value

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (ie. P000000010)
    collection_id : str
        The collection where the instance.json is to fill (ie. C000000002)
    """
    from datetime import datetime

    current_user = ctx.callback.get_client_username("")["arguments"][0]
    collection_path = "/nlmumc/projects/{}/{}".format(project_id, collection_id)

    ctx.callback.msiSetACL("recursive", "own", current_user, collection_path)

    metadata_folder_path = collection_path + "/.metadata_versions"
    metadata_folder_exist = True

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
            ctx.callback.closeProjectCollection(project_id, collection_id)
            ctx.callback.msiExit("-1", "ERROR: Couldn't create '{}'".format(metadata_folder_path))

    source_schema = collection_path + "/schema.json"
    source_instance = collection_path + "/instance.json"

    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f')

    destination_schema = metadata_folder_path + "/schema_{}.json".format(timestamp)
    destination_instance = metadata_folder_path + "/instance_{}.json".format(timestamp)

    # Copy current metadata json files to /.metadata_versions
    try:
        ctx.callback.msiDataObjCopy(source_schema, destination_schema, "", 0)
        ctx.callback.msiDataObjCopy(source_instance, destination_instance, "", 0)
    except RuntimeError:
        ctx.callback.closeProjectCollection(project_id, collection_id)
        ctx.callback.msiExit("-1", "ERROR: Couldn't create the metadata snapshots '{}'".format(metadata_folder_path))

    # Overwriting the schema:isBasedOn with the MDR schema handle URL
    mdr_handle_url = ctx.callback.msi_getenv("MDR_HANDLE_URL", "")["arguments"][1]
    schema_url_extension = "{}/{}/schema_{}".format(project_id, collection_id, timestamp)
    schema_url = "{}{}".format(mdr_handle_url, schema_url_extension)
    try:
        ctx.callback.update_instance_snapshot(destination_instance, schema_url)
    except RuntimeError:
        ctx.callback.closeProjectCollection(project_id, collection_id)
        ctx.callback.msiExit("-1", "ERROR: Couldn't update the instance snapshot '{}'".format(destination_instance))
