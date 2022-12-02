# ./run_test.sh -r open_project_collection_snapshot -a "P000000014,C000000001,rods,admin:own"
from datahubirodsruleset.core import make, Output, format_project_collection_path, format_schema_collection_path, \
    format_instance_collection_path, format_metadata_versions_path


@make(inputs=range(4), outputs=[], handler=Output.STORE)
def open_project_collection_snapshot(ctx, project_id, collection_id, username, access):
    """
    This rule opens a project collection root, the schema.json , instance.json and the .metadata_versions sub-folder
    in order to add, modify or delete data by a user. It uses parameters for username and access.
    Is does NOT open recursively.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project ID e.g: P000000001
    collection_id: str
        The collection ID e.g: C000000001
    username: str
        The username
    access: str
        ownership rights
    """

    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    schema_path = format_schema_collection_path(ctx, project_id, collection_id)
    instance_path = format_instance_collection_path(ctx, project_id, collection_id)
    metadata_folder_path = format_metadata_versions_path(ctx, project_id, collection_id)

    ctx.callback.msiSetACL("default", access, username, project_collection_path)
    ctx.callback.msiSetACL("default", access, username, schema_path)
    ctx.callback.msiSetACL("default", access, username, instance_path)

    try:
        ctx.callback.msiSetACL("default", access, username, metadata_folder_path)
    except RuntimeError:
        # Only print an error message if the sub folder '.metadata_versions' doesn't exist
        # Because the user have been granted write access on the collection's root, '.metadata_versions' will be created
        # during the execution of create_collection_metadata_snapshot and therefore have write access to it.
        ctx.callback.msiWriteRodsLog(
            "DEBUG: '{}' doesn't exist yet while setting ACL for rods in open_project_collection_snapshot".format(
                metadata_folder_path
            ),
            0,
        )
