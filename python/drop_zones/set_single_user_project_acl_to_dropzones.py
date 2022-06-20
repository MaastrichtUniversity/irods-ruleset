# /rules/tests/run_test.sh -r set_single_user_project_acl_to_dropzones -a "P000000014,dlinssen"
@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def set_single_user_project_acl_to_dropzones(ctx, project_id, username):
    """
    This rule transfers the ACLs of the input user that exist on a project level to all of its dropzones
    - Get the 'enableDropzoneSharing' avu on the project
    - Get all dropzones for the project
    - For each dropzone, depending on the enableDropzoneSharing avu and creator perform the following:
        - Remove this person from the dropzone ACLs
        - Add this person to a dropzone with 'own' rights

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The id of the project to transfer the ACLs from to it's dropzone
    username: str
        The name of the user or group to modify the dropzone ACLs for
    """
    project_path = format_project_path(ctx, project_id)

    sharing_enabled = ctx.callback.getCollectionAVU(project_path, "enableDropzoneSharing", "", "", FALSE_AS_STRING)["arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)

    # If the AVU is not enabled, stop the rule's execution
    if not sharing_enabled:
        return

    prefix = ""
    # If the user calling this rule is 'rods' we need to escalate
    if ctx.callback.get_client_username("")["arguments"][0] == "rods":
        prefix = "admin:"

    query_parameters = "COLL_NAME"
    query_conditions = "COLL_PARENT_NAME = '/nlmumc/ingest/direct' " \
                       "AND META_COLL_ATTR_NAME = 'project' " \
                       "AND META_COLL_ATTR_VALUE = '{}'".format(project_id)

    for item in row_iterator(query_parameters, query_conditions, AS_LIST, ctx.callback):
        dropzone_path = item[0]
        creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", FALSE_AS_STRING)["arguments"][2]
        dropzone_state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", FALSE_AS_STRING, FALSE_AS_STRING)[
            "arguments"][2]

        # Check if the dropzone is still in an ingestable state
        ingestable = ctx.callback.is_dropzone_state_ingestable(dropzone_state, "")["arguments"][1]
        if not formatters.format_string_to_boolean(ingestable):
            continue

        # Do not revoke / add permissions if the creator's permissions were changed on the project
        if sharing_enabled and username != creator:
            privilege = get_username_permission(ctx, project_path, username)
            if privilege == "own" or privilege == "modify object":
                set_single_own_permissions_dropzone(ctx, dropzone_path, username, prefix)
            else:
                revoke_single_permissions_dropzone(ctx, dropzone_path, username, prefix)


def set_single_own_permissions_dropzone(ctx, dropzone_path, username, admin_prefix):
    """
    Set the user to the input dropzone with 'own' rights recursively.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path : str
        The absolute dropzone path; e.g: /nlmumc/ingest/direct/crazy-frog
    username: str
        The user that the permission need to be changed
    admin_prefix: str
        If the client user is an admin, set the ACL with admin mode
    """
    ctx.callback.msiSetACL("recursive", admin_prefix + "own", username, dropzone_path)
    ctx.callback.msiSetACL("default", admin_prefix + "read", username, dropzone_path + "/instance.json")
    ctx.callback.msiSetACL("default", admin_prefix + "read", username, dropzone_path + "/schema.json")


def revoke_single_permissions_dropzone(ctx, dropzone_path, username, admin_prefix):
    """
    Revoke recursively the user permissions on the dropzone.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path : str
        The absolute dropzone path; e.g: /nlmumc/ingest/direct/crazy-frog
    username: str
        The user that the permission need to be changed
    admin_prefix: str
        If the client user is an admin, set the ACL with admin mode
    """
    ctx.callback.msiSetACL("recursive", admin_prefix + "null", username, dropzone_path)


def get_username_permission(ctx, project_path, username):
    """
    Query the input user permission for the input path.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        The absolute path of the project to query.
    username: str
        The username to query.

    Returns
    -------
    str
        The user permission/access name
    """
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    access_name = ""
    for result in row_iterator(
        "COLL_ACCESS_NAME",
        "COLL_ACCESS_USER_ID = '{}' AND ".format(user_id) + "COLL_NAME = '{}'".format(project_path),
        AS_LIST,
        ctx.callback,
    ):
        access_name = result[0]
    return access_name
