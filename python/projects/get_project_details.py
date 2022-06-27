# ./run_test.sh -r get_project_details -a "/nlmumc/projects/P000000014,false" -u dlinssen -j
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
    username = ctx.callback.get_client_username("")["arguments"][0]

    has_financial_view_access = False
    # Initialize the project dictionary
    project = {}

    project["path"] = project_path
    project["project"] = formatters.get_project_id_from_project_path(project_path)

    # List Contributors
    ret = ctx.callback.list_project_contributors(project["project"], FALSE_AS_STRING, show_service_accounts, "")["arguments"][3]
    project["contributors"] = json.loads(ret)

    # List Managers
    ret = ctx.callback.list_project_managers(project["project"], show_service_accounts, "")["arguments"][2]
    project["managers"] = json.loads(ret)

    # List Viewers
    ret = ctx.callback.list_project_viewers(project["project"], FALSE_AS_STRING, show_service_accounts, "")["arguments"][3]
    project["viewers"] = json.loads(ret)

    # Get project metadata
    # Note: Retrieving the rule outcome is done with '["arguments"][2]'
    project["title"] = ctx.callback.getCollectionAVU(project["path"], "title", "", "", TRUE_AS_STRING)["arguments"][2]
    project["enableOpenAccessExport"] = ctx.callback.getCollectionAVU(
        project["path"], "enableOpenAccessExport", "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    project["enableArchive"] = ctx.callback.getCollectionAVU(project["path"], "enableArchive", "", FALSE_AS_STRING, FALSE_AS_STRING)[
        "arguments"
    ][2]
    project["enableUnarchive"] = ctx.callback.getCollectionAVU(
        project["path"], "enableUnarchive", "", project["enableArchive"], FALSE_AS_STRING
    )["arguments"][2]
    project["enableContributorEditMetadata"] = ctx.callback.getCollectionAVU(
        project["path"], "enableContributorEditMetadata", "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    project["respCostCenter"] = ctx.callback.getCollectionAVU(project["path"], "responsibleCostCenter", "", "", TRUE_AS_STRING)[
        "arguments"
    ][2]
    project["storageQuotaGiB"] = ctx.callback.getCollectionAVU(project["path"], "storageQuotaGb", "", "", TRUE_AS_STRING)[
        "arguments"
    ][2]
    project["collectionMetadataSchemas"] = ctx.callback.getCollectionAVU(
        project["path"], "collectionMetadataSchemas", "", "", TRUE_AS_STRING
    )["arguments"][2]
    project["enableDropzoneSharing"] = ctx.callback.getCollectionAVU(
        project["path"], "enableDropzoneSharing", "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]

    ret = ctx.callback.getCollectionAVU(project["path"], "OBI:0000103", "", "", TRUE_AS_STRING)["arguments"][2]
    if ret == username:
        has_financial_view_access = True
    # Get the display name value for the PI
    for user in project["managers"]["userObjects"]:
        if user["userName"] == ret:
            project["principalInvestigatorDisplayName"] = user["displayName"]

    ret = ctx.callback.getCollectionAVU(project["path"], "dataSteward", "", "", TRUE_AS_STRING)["arguments"][2]
    if ret == username:
        has_financial_view_access = True
    # Get the display name value for the data steward
    for user in project["managers"]["userObjects"]:
        if user["userName"] == ret:
            project["dataStewardDisplayName"] = user["displayName"]

    project["has_financial_view_access"] = has_financial_view_access

    # Calculate the project's size
    ret = ctx.callback.get_project_size(project["path"], "")["arguments"][1]
    project["dataSizeGiB"] = json.loads(ret)

    return project
