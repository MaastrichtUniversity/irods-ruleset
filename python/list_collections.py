@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_collections(ctx, project_path):
    """
    Get a listing of all (authorized) projects

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_path:
        Project absolute path

    Returns
    -------
    list
        a json list of projects objects
    """
    # Get the client username
    username = ''
    var_map = session_vars.get_map(ctx.rei)
    user_type = 'client_user'
    userrec = var_map.get(user_type, '')
    if userrec:
        username = userrec.get('user_name', '')

    has_financial_view_access = False
    # Initialize the project dictionary
    project = {}

    project["path"] = project_path
    project["project"] = project["path"].split("/")[3]

    # List Contributors
    ret = ctx.callback.listProjectContributors(project["project"], "false", "")["arguments"][2]
    project["contributors"] = json.loads(ret)

    # List Managers
    ret = ctx.callback.listProjectManagers(project["project"], "")["arguments"][1]
    project["managers"] = json.loads(ret)

    # List Viewers
    ret = ctx.callback.listProjectViewers(project["project"], "false", "")["arguments"][2]
    project["viewers"] = json.loads(ret)

    # Get project metadata
    # Note: Retrieving the rule outcome is done with '["arguments"][2]'
    project["title"] = ctx.callback.getCollectionAVU(project["path"], "title", "", "", "true")["arguments"][2]
    project["enableOpenAccessExport"] = \
    ctx.callback.getCollectionAVU(project["path"], "enableOpenAccessExport", "", "false", "false")["arguments"][2]
    project["enableArchive"] = \
    ctx.callback.getCollectionAVU(project["path"], "enableArchive", "", "false", "false")["arguments"][2]
    project["respCostCenter"] = \
    ctx.callback.getCollectionAVU(project["path"], "responsibleCostCenter", "", "", "true")["arguments"][2]
    project["storageQuotaGiB"] = \
    ctx.callback.getCollectionAVU(project["path"], "storageQuotaGb", "", "", "true")["arguments"][2]

    ret = ctx.callback.getCollectionAVU(project["path"], "OBI:0000103", "", "", "true")["arguments"][2]
    if ret == username:
        has_financial_view_access = True
    # Get the display name value for the PI
    for user in project["managers"]['userObjects']:
        if user['userName'] == ret:
            project["principalInvestigatorDisplayName"] = user['displayName']

    ret = ctx.callback.getCollectionAVU(project["path"], "dataSteward", "", "", "true")["arguments"][2]
    if ret == username:
        has_financial_view_access = True
    # Get the display name value for the data steward
    for user in project["managers"]['userObjects']:
        if user['userName'] == ret:
            project["dataStewardDisplayName"] = user['displayName']

    project["has_financial_view_access"] = has_financial_view_access

    # Initialize the collections dictionary
    collections = []

    proj_size = float(0)
    for proj_coll in row_iterator("COLL_NAME",
                                  "COLL_PARENT_NAME = '" + project["path"] + "'",
                                  AS_LIST,
                                  ctx.callback):
        # Calculate size for entire project
        coll_size = float(ctx.callback.get_collection_size(proj_coll[0], "GiB", "none", "")["arguments"][3])
        proj_size = proj_size + coll_size

        # Initialize the collections dictionary
        collection = {}

        collection["id"] = proj_coll[0].split("/")[4]

        # Get AVUs
        collection["size"] = coll_size
        collection["title"] = ctx.callback.getCollectionAVU(proj_coll[0], "title", "", "", "false")["arguments"][2]
        collection["creator"] = ctx.callback.getCollectionAVU(proj_coll[0], "creator", "", "", "false")["arguments"][2]
        collection["PID"] = ctx.callback.getCollectionAVU(proj_coll[0], "PID", "", "", "false")["arguments"][2]
        collection["numFiles"] = ctx.callback.getCollectionAVU(proj_coll[0], "numFiles", "", "", "false")["arguments"][2]

        collections.append(collection)

    project["dataSizeGiB"] = proj_size

    output = {
        "project": project,
        "collections": collections
    }

    return output
