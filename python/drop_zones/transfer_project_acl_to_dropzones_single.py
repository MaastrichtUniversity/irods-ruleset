# /rules/tests/run_test.sh -r transfer_project_acl_to_dropzones_single -a "P000000014,dlinssen"
@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def transfer_project_acl_to_dropzones_single(ctx, project_id, username):
    """
    This rule transfers the ACLs that exist on a project level to all of its dropzones
    - Get the 'enableDropzoneSharing' avu on the project
    - Get all dropzones for the project
    - For each dropzone, depending on the enableDropzoneSharing avu and creator perform the following:
        - Remove this person from the dropzone ACLs
        - Add this person to a dropzone with 'own' rights

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The id of the project to transfer the ACLs from to it's dropzone
    username: str
         The name of the user or group to modify the dropzone ACLs for
    """
    project_path = format_project_path(ctx, project_id)

    sharing_enabled = ctx.callback.getCollectionAVU(project_path, "enableDropzoneSharing", "", "", FALSE_AS_STRING)["arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)
    prefix = ""

    # If the user calling this rule is 'rods' we need to escalate
    if ctx.callback.get_client_username("")["arguments"][0] == "rods":
        prefix = "admin:"

    for item in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE", "COLL_PARENT_NAME = '/nlmumc/ingest/direct' AND META_COLL_ATTR_NAME = 'project' AND META_COLL_ATTR_VALUE = '{}'".format(project_id), AS_LIST, ctx.callback):
        dropzone_path = item[0]
        creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", FALSE_AS_STRING)["arguments"][2]

        # Do not revoke / add permissions if the creator's permissions were changed on the project
        if sharing_enabled and username != creator:
            privileges = get_username_privileges(ctx, project_path, username)
            if privileges == "own" or privileges == "modify object":
                set_single_own_permissions_dropzone(ctx, dropzone_path, username, prefix)
            else:
                revoke_single_permissions_dropzone(ctx, dropzone_path, username, prefix)


def set_single_own_permissions_dropzone(ctx, dropzone_path, username, prefix):
    ctx.callback.msiSetACL("recursive", prefix + "own", username, dropzone_path)
    ctx.callback.msiSetACL("default", prefix + "read", username, dropzone_path + "/instance.json")
    ctx.callback.msiSetACL("default", prefix + "read", username, dropzone_path + "/schema.json")


def revoke_single_permissions_dropzone(ctx, dropzone_path, username, prefix):
    ctx.callback.msiSetACL("recursive", prefix + "null", username, dropzone_path)


def get_username_privileges(ctx, path, username):
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    access_name = ""
    for result in row_iterator(
        "COLL_ACCESS_NAME",
        "COLL_ACCESS_USER_ID = '{}' AND ".format(user_id) + "COLL_NAME = '{}'".format(path),
        AS_LIST,
        ctx.callback,
    ):
        access_name = result[0]
    return access_name
