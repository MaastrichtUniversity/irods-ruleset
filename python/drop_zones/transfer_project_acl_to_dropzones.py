# /rules/tests/run_test.sh -r transfer_project_acl_to_dropzones -a "P000000014"
@make(inputs=[0], outputs=[], handler=Output.STORE)
def transfer_project_acl_to_dropzones(ctx, project_id):
    """
    This rule transfers the ACLs that exist on a project level to all of its dropzones
    - Get the 'enableDropzoneSharing' avu on the project
    - Get all dropzones for the project
    - For each dropzone, depending on the enableDropzoneSharing avu perform the following:
        - Remove all contributors and managers from the dropzones except for the creator
        - Add all contributors and managers to a dropzone with 'own' rights

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The id of the project to transfer the ACLs from to it's dropzones
    """
    project_path = format_project_path(ctx, project_id)

    sharing_enabled = \
    ctx.callback.getCollectionAVU(project_path, "enableDropzoneSharing", "", FALSE_AS_STRING, FALSE_AS_STRING)[
        "arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)

    prefix = ""
    caller = ctx.callback.get_client_username("")["arguments"][0]
    # If the user calling this rule is 'rods' we need to escalate
    if caller == "rods":
        prefix = "admin:"

    for item in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                             "COLL_PARENT_NAME = '/nlmumc/ingest/direct' AND META_COLL_ATTR_NAME = 'project' AND META_COLL_ATTR_VALUE = '{}'".format(
                                     project_id), AS_LIST, ctx.callback):
        dropzone_path = item[0]
        if sharing_enabled:
            contributors = get_contributors_for_project(ctx, project_path)
            set_own_permissions_dropzone(ctx, dropzone_path, contributors, prefix)
        else:
            contributors = get_contributors_for_project(ctx, dropzone_path)
            creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
            revoke_permissions_dropzone(ctx, dropzone_path, contributors, creator, prefix)


def set_own_permissions_dropzone(ctx, dropzone_path, contributors, prefix):
    for contributor in contributors:
        ctx.callback.msiSetACL("recursive", prefix + "own", contributor, dropzone_path)
        ctx.callback.msiSetACL("default", prefix + "read", contributor, dropzone_path + "/instance.json")
        ctx.callback.msiSetACL("default", prefix + "read", contributor, dropzone_path + "/schema.json")


def revoke_permissions_dropzone(ctx, dropzone_path, contributors, creator, prefix):
    # Remove permissions of all contributors
    for contributor in contributors:
        ctx.callback.msiSetACL("recursive", prefix + "null", contributor, dropzone_path)

    # Give creator back permissions
    ctx.callback.msiSetACL("recursive", prefix + "own", creator, dropzone_path)
    ctx.callback.msiSetACL("default", prefix + "read", creator, dropzone_path + "/instance.json")
    ctx.callback.msiSetACL("default", prefix + "read", creator, dropzone_path + "/schema.json")


def get_contributors_for_project(ctx, path):
    criteria = "'own', 'modify object'"
    output = []
    for result in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE",
        "COLL_ACCESS_NAME in ({}) AND ".format(criteria) + "COLL_NAME = '{}'".format(path),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]

        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            account_type = account[1]

            if account_type != "rodsadmin" and "service-" not in account_name:
                output.append(account_name)

    return output
