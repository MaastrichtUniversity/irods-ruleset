@make(inputs=range(5), outputs=[], handler=Output.STORE)
def set_acl_for_metadata_snapshot(ctx, project_id, collection_id, username, open_acl, close_acl):
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
    username: str
        The username
    open_acl: str
        'true'/'false' expected; If true, open the collection ACL for the current user
    close_acl: str
        'true'/'false' expected; If true, open the collection ACL for the current user
    """

    access = "read"
    if formatters.format_string_to_boolean(open_acl):
        ctx.callback.open_project_collection_snapshot(project_id, collection_id, "rods", "admin:own")
        access = "write"

    ctx.callback.open_project_collection_snapshot(project_id, collection_id, username, access)

    if formatters.format_string_to_boolean(close_acl):
        set_collection_size_call = "setCollectionSize('{}', '{}', 'false', 'false')".format(project_id, collection_id)
        close_project_collection_snapshot_user_call = "close_project_collection_snapshot('{}', '{}', '{}')".format(
            project_id, collection_id, username
        )
        close_project_collection_snapshot_rods_call = "close_project_collection_snapshot('{}', '{}', '{}')".format(
            project_id, collection_id, "rods"
        )
        ctx.delayExec(
            "<PLUSET>1s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            "{};{};{};".format(
                set_collection_size_call,
                close_project_collection_snapshot_user_call,
                close_project_collection_snapshot_rods_call,
            ),
            "",
        )
