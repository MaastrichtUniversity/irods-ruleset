@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_details(ctx, project_path):
    """
    Get a listing of all (authorized) projects

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    list
        a json list of projects objects
    """
        
    # Reset the project dictionary
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
    project["enableOpenAccessExport"] = ctx.callback.getCollectionAVU(project["path"], "enableOpenAccessExport", "", "false", "false")["arguments"][2]
    project["enableArchive"] = ctx.callback.getCollectionAVU(project["path"], "enableArchive", "", "false", "false")["arguments"][2]
    project["respCostCenter"] = ctx.callback.getCollectionAVU(project["path"], "responsibleCostCenter", "", "", "true")["arguments"][2]
    project["storageQuotaGiB"] = ctx.callback.getCollectionAVU(project["path"], "storageQuotaGb", "", "", "true")["arguments"][2]
    
    # Get the display name value for PI and data steward
    ret = ctx.callback.getCollectionAVU(project["path"], "OBI:0000103", "", "", "true")["arguments"][2]
    for user in project["managers"]['userObjects']:
        if user['userName'] == ret:
            project["principalInvestigatorDisplayName"] = user['displayName']
    
    ret = ctx.callback.getCollectionAVU(project["path"], "dataSteward", "", "", "true")["arguments"][2]
    for user in project["managers"]['userObjects']:
        if user['userName'] == ret:
            project["dataStewardDisplayName"] = user['displayName']
    
    # Calculate size for entire project
    proj_size = float(0)
    for proj_coll in row_iterator("COLL_NAME",
                                  "COLL_PARENT_NAME = '" + project["path"] + "'",
                                  AS_LIST,
                                  ctx.callback):
        coll_size = float(ctx.callback.get_collection_size(proj_coll[0], "GiB", "none", "")["arguments"][3])
        proj_size = proj_size + coll_size
    
    project["dataSizeGiB"] = proj_size
    
    return project