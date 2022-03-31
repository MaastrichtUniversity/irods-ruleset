@make(inputs=range(5), outputs=[], handler=Output.STORE)
def set_acl_for_metadata_snapshot(ctx, project_id, collection_id, user, open_acl, close_acl):
    """
    Modify the ACL of the given project collection for the given user to be able to create the metadata snapshot.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The project ID ie P000000001
    collection_id: str
        The collection ID ie C000000001
    user: str
        The username
    open_acl: str
        'true'/'false' expected; If true, open the collection ACL for the current user
    close_acl: str
        'true'/'false' expected; If true, open the collection ACL for the current user
    """
    collection_path = format_project_collection_path(ctx, project_id, collection_id)
    schema_path = format_schema_collection_path(ctx, project_id, collection_id)
    instance_path = format_instance_collection_path(ctx, project_id, collection_id)
    access = "read"
    if formatters.format_string_to_boolean(open_acl):
        ctx.callback.openProjectCollection(project_id, collection_id, "rods", "own")
        access = "write"
    ctx.callback.msiSetACL("default", access, user, collection_path)
    ctx.callback.msiSetACL("default", access, user, schema_path)
    ctx.callback.msiSetACL("default", access, user, instance_path)

    metadata_folder_path = format_metadata_versions_path(ctx, project_id, collection_id)
    try:
        ctx.callback.msiSetACL("default", access, user, metadata_folder_path)
    except RuntimeError:
        # Only print an error message if the sub folder '.metadata_versions' doesn't exist
        # Because the user have been granted write access on the collection's root, '.metadata_versions' will be created
        # during the execution of create_collection_metadata_snapshot and therefore have write access to it.
        ctx.callback.msiWriteRodsLog("DEBUG: '{}' doesn't exist yet".format(metadata_folder_path), 0)

    if formatters.format_string_to_boolean(close_acl):
        ctx.callback.closeProjectCollection(project_id, collection_id)
