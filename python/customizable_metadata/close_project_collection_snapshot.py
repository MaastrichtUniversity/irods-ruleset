# ./run_test.sh -r close_project_collection_snapshot -a "P000000014,C000000001,psuppers"
@make(inputs=range(3), outputs=[], handler=Output.STORE)
def close_project_collection_snapshot(ctx, project_id, collection_id, username):
    """
    This rule closes a project collection root, the schema.json , instance.json and the .metadataversions subfolder
    for both rods and the specified user.  It only closes the .metadataversions recursively

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The project ID ie P000000001
    collection_id: str
        The collection ID ie C000000001
    username: str
        The username
    """

    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    schema_path = format_schema_collection_path(ctx, project_id, collection_id)
    instance_path = format_instance_collection_path(ctx, project_id, collection_id)
    metadata_folder_path = format_metadata_versions_path(ctx, project_id, collection_id)

    ctx.callback.msiSetACL("default", "read", username, schema_path)
    ctx.callback.msiSetACL("default", "read", username, instance_path)
    try:
        ctx.callback.msiSetACL("recursive", "read", username, metadata_folder_path)
    except RuntimeError:
        # Only print an error message if the sub folder '.metadata_versions' doesn't exist
        # Because the user have been granted write access on the collection's root, '.metadata_versions' will be created
        # during the execution of create_collection_metadata_snapshot and therefore have write access to it.
        ctx.callback.msiWriteRodsLog(
            "DEBUG: '{}' doesn't exist yet while setting ACL for '{}' in close_project_collection_snapshot".format(
                metadata_folder_path, username
            ),
            0,
        )

    ctx.callback.msiSetACL("default", "read", username, project_collection_path)
