# ./run_test.sh -r transfer_project_acl_to_dropzone -a "P000000014,false"
@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def transfer_project_acl_to_dropzone(ctx, project_id, new_dropzone):
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
    new_dropzone: bool
        Transfer the ACL for a new dropzone
    """

    project_path = format_project_path(ctx, project_id)
    new_dropzone = formatters.format_string_to_boolean(new_dropzone)

    sharing_enabled = ctx.callback.getCollectionAVU(project_path, "enableDropzoneSharing", "", FALSE_AS_STRING, FALSE_AS_STRING)["arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)

    for item in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE", "COLL_PARENT_NAME = '/nlmumc/ingest/direct' AND META_COLL_ATTR_NAME = 'project' AND META_COLL_ATTR_VALUE = '{}'".format(project_id), AS_LIST, ctx.callback):
        dropzone_path = item[0]
        if sharing_enabled:
            contributors = get_contributors_for_project(ctx, project_path)
            set_own_permissions_dropzone(ctx, dropzone_path, contributors, new_dropzone)
        else:
            contributors = get_contributors_for_project(ctx, dropzone_path)
            creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
            revoke_permissions_dropzone(ctx, dropzone_path, contributors, creator)


def set_own_permissions_dropzone(ctx, dropzone_path, contributors, new_dropzone):
    for contributor in contributors:
        ctx.callback.msiSetACL("recursive", "own", contributor["account_name"], dropzone_path)
        if not new_dropzone:
            ctx.callback.msiSetACL("default", "read", contributor["account_name"], dropzone_path + "/instance.json")
            ctx.callback.msiSetACL("default", "read", contributor["account_name"], dropzone_path + "/schema.json")


def revoke_permissions_dropzone(ctx, dropzone_path, contributors, creator):
    for contributor in contributors:
        ctx.callback.msiSetACL("recursive", "null", contributor["account_name"], dropzone_path)
    ctx.callback.msiSetACL("recursive", "own", creator, dropzone_path)
    ctx.callback.msiSetACL("default", "read", creator, dropzone_path + "/instance.json")
    ctx.callback.msiSetACL("default", "read", creator, dropzone_path + "/schema.json")


def get_contributors_for_project(ctx, path):
    criteria = "'own', 'modify object'"

    output = []
    for result in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE",
        "COLL_ACCESS_NAME in ({}) AND ".format(criteria) + "COLL_NAME = '{}'".format(path),
        AS_LIST,
        ctx.callback,
    ):
        access_name = result[1]
        access_type = result[2]
        account_id = result[0]
        account_name = ""
        account_type = ""

        access = {"account_id": account_id, "access_name": access_name, "access_type": access_type}

        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            account_type = account[1]

            access["account_name"] = account_name
            access["account_type"] = account_type

        if account_type != "rodsadmin" and "service-" not in access["account_name"]:
            output.append(access)

    return output
