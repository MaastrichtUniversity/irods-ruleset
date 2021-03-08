@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_details(ctx, project_path, show_service_accounts):
    """
    Get the all the project's AVU

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_path: str
        Project absolute path
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    list
        a json list of projects objects
    """
    username = ctx.callback.get_client_username('')["arguments"][0]

    has_financial_view_access = False
    # Initialize the project dictionary
    project = {}
    
    project["path"] = project_path
    project["project"] = project["path"].split("/")[3]
    
    # List Contributors
    ret = ctx.callback.listProjectContributors(project["project"], "false", "")["arguments"][2]
    project["contributors"] = json.loads(ret)
    
    # List Managers
    ret = ctx.callback.list_project_managers(project["project"], show_service_accounts, "")["arguments"][2]
    project["managers"] = json.loads(ret)
    
    # List Viewers
    ret = ctx.callback.listProjectViewers(project["project"], "false", "")["arguments"][2]
    project["viewers"] = json.loads(ret)


    # TODO
    # Rewrite listProjectViewers, listProjectViewers, listProjectContributors
    # to add a new parameter show_service_accounts
    # Filtering out the service accounts here, might cause to slow down the query performance
    if show_service_accounts == "false":
        for viewer in project["viewers"]['userObjects']:
            if "service-" in viewer['userName']:
                project["viewers"]['userObjects'].remove(viewer)

        for viewer in project["viewers"]['users']:
            if "service-" in viewer:
                project["viewers"]['users'].remove(viewer)

        for contributor in project["contributors"]['userObjects']:
            if "service-" in contributor['userName']:
                project["contributors"]['userObjects'].remove(contributor)
        for contributor in project["contributors"]['users']:
            if "service-" in contributor:
                project["contributors"]['users'].remove(contributor)

    # Get project metadata
    # Note: Retrieving the rule outcome is done with '["arguments"][2]'
    project["title"] = ctx.callback.getCollectionAVU(project["path"], "title", "", "", "true")["arguments"][2]
    project["enableOpenAccessExport"] = ctx.callback.getCollectionAVU(project["path"], "enableOpenAccessExport", "", "false", "false")["arguments"][2]
    project["enableArchive"] = ctx.callback.getCollectionAVU(project["path"], "enableArchive", "", "false", "false")["arguments"][2]
    project["respCostCenter"] = ctx.callback.getCollectionAVU(project["path"], "responsibleCostCenter", "", "", "true")["arguments"][2]
    project["storageQuotaGiB"] = ctx.callback.getCollectionAVU(project["path"], "storageQuotaGb", "", "", "true")["arguments"][2]
    
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

    # Calculate the project's size
    ret = ctx.callback.get_project_size(project["path"], '')["arguments"][1]
    project["dataSizeGiB"] = json.loads(ret)

    return project
