@make(inputs=[0], outputs=[1], handler=Output.STORE)
def check_edit_metadata_permission(ctx, project_path):
    """
    Return boolean if the current user is allowed to edit metadata for a given project

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_path: str
        Project absolute path
    Returns
    -------
    boolan
       whether current user is allowed to edit metadata for project
    """

    username = ctx.callback.get_client_username("")["arguments"][0]
    project = project_path.split("/")[3]
    ret = ctx.callback.get_user_group_memberships("false", username, "")["arguments"][2]
    groups = json.loads(ret)

    # If user is the Principal Investigator he is allowed to edit the metadata
    # If this query fails, the user has no rights to this project or project does not exist so False should be returned
    try:
        ret = ctx.callback.getCollectionAVU(project_path, "OBI:0000103", "", "", "true")["arguments"][2]
        if ret == username:
            return True
    except RuntimeError:
        return False

    # If user is the Data Steward he is allowed to edit the metadata
    ret = ctx.callback.getCollectionAVU(project_path, "dataSteward", "", "", "true")["arguments"][2]
    if ret == username:
        return True

    # If user is a manager or in one of the managing groups he is allowed to edit the metadata
    ret = ctx.callback.list_project_managers(project, "false", "")["arguments"][2]
    managers = json.loads(ret)
    if username in managers["users"]:
        return True
    for group in groups:
        if group["name"] in managers["groups"]:
            return True

    # If user is a contributor or in one of the contributing groups and enableContributorEditMetadata is true he is allowed to edit the metadata
    ret = ctx.callback.getCollectionAVU(project_path, "enableContributorEditMetadata", "", "", "false")["arguments"][2]
    if ret == "true":
        ret = ctx.callback.list_project_contributors(project, "false", "false", "")["arguments"][3]
        contributors = json.loads(ret)
        if username in contributors["users"]:
            return True
        for group in groups:
            if group["name"] in contributors["groups"]:
                return True

    return False
