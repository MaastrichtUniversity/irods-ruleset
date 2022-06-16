# /rules/tests/run_test.sh -r set_project_acl_to_dropzone -a "P000000014,nervous-reindeer,false"
@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def set_project_acl_to_dropzone(ctx, project_id, dropzone_token, new_dropzone):
    """
    This rule transfers the ACLs that exist on the input project level to the input dropzone.
        * Get the 'enableDropzoneSharing' avu on the project
        * Depending on the enableDropzoneSharing avu perform the following:
            * False -> Remove all contributors and managers from the dropzone except for the creator
            * True  -> Add all contributors and managers to a dropzone with 'own' rights

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The id of the project to transfer the ACLs from to it's dropzone; e.g: P000000010
    dropzone_token : str
        The dropzone token; e.g: crazy-frog
    new_dropzone : str
        'true'/'false' expected; If true, the input dropzone has been newly created
    """
    project_path = format_project_path(ctx, project_id)
    dropzone_path = format_dropzone_path(ctx, dropzone_token, "direct")

    sharing_enabled = \
    ctx.callback.getCollectionAVU(project_path, "enableDropzoneSharing", "", FALSE_AS_STRING, FALSE_AS_STRING)[
        "arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)
    new_dropzone = formatters.format_string_to_boolean(new_dropzone)

    prefix = ""
    caller = ctx.callback.get_client_username("")["arguments"][0]
    # If the user calling this rule is 'rods' we need to escalate
    if caller == "rods":
        prefix = "admin:"

    if sharing_enabled:
        contributors = get_contributors_for_project_or_dropzone(ctx, project_path)
        set_own_permissions_dropzone(ctx, dropzone_path, contributors, prefix)
    elif not sharing_enabled and not new_dropzone:
        contributors = get_contributors_for_project_or_dropzone(ctx, dropzone_path)
        revoke_permissions_dropzone(ctx, dropzone_path, contributors, prefix)


def set_own_permissions_dropzone(ctx, dropzone_path, contributors, admin_prefix):
    """
    Set recursively all project contributors and managers to the input dropzone with 'own' rights.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path : str
        The absolute dropzone path; e.g: /nlmumc/ingest/direct/crazy-frog
    contributors: list[str]
        List of the project's contributors usernames.
    admin_prefix: str
        If the client user is an admin, set the ACL with admin mode
    """
    for contributor in contributors:
        ctx.callback.msiSetACL("recursive", admin_prefix + "own", contributor, dropzone_path)
        ctx.callback.msiSetACL("default", admin_prefix + "read", contributor, dropzone_path + "/instance.json")
        ctx.callback.msiSetACL("default", admin_prefix + "read", contributor, dropzone_path + "/schema.json")


def revoke_permissions_dropzone(ctx, dropzone_path, contributors, admin_prefix):
    """
    Revoke recursively all the user permissions on the dropzone. And then re-set the creator permissions.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path : str
        The absolute dropzone path; e.g: /nlmumc/ingest/direct/crazy-frog
    contributors: list[str]
        List of the project's contributors usernames.
    admin_prefix: str
        If the client user is an admin, set the ACL with admin mode
    """
    # Remove permissions of all contributors
    for contributor in contributors:
        ctx.callback.msiSetACL("recursive", admin_prefix + "null", contributor, dropzone_path)

    creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
    # Give creator back permissions
    ctx.callback.msiSetACL("recursive", admin_prefix + "own", creator, dropzone_path)
    ctx.callback.msiSetACL("default", admin_prefix + "read", creator, dropzone_path + "/instance.json")
    ctx.callback.msiSetACL("default", admin_prefix + "read", creator, dropzone_path + "/schema.json")


def get_contributors_for_project_or_dropzone(ctx, path):
    """
    Query the list of contributors usernames of the input path

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    path: str
        The absolute path of the project or dropzone to query.

    Returns
    -------
    list[str]
        List of the project's contributors usernames.
    """
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
