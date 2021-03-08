@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_managing_project(ctx, project_id, show_service_accounts):
    """
    Query the list of ACL for a project for the client user

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id : str
        The project's id; eg.g P000000010
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        The list of usernames for managers, contributors and viewers.
        Returns an empty list if the user is not a manager.
    """
    username = ctx.callback.get_client_username('')["arguments"][0]
    username = "psuppers"

    managers = ctx.callback.list_project_managers(project_id, show_service_accounts, "managers")["arguments"][2]
    managers = json.loads(managers)

    # if the user is not part of the managers, return an empty list
    if username not in managers['users']:
        return []

    contributors = ctx.callback.list_project_contributors(project_id, "false", show_service_accounts, "")["arguments"][3]
    contributors = json.loads(contributors)

    result = ctx.callback.listProjectViewers(project_id, 'false', "viewers")
    viewers = result["arguments"][2]
    viewers = json.loads(viewers)

    project_path = "/nlmumc/projects/" + project_id

    principal_investigator = ctx.callback.getCollectionAVU(project_path, "OBI:0000103", "", "", "true")["arguments"][2]
    data_steward = ctx.callback.getCollectionAVU(project_path, "dataSteward", "", "", "true")["arguments"][2]

    output = {
        "managers": managers,
        "contributors": contributors,
        "viewers": viewers,
        "principal_investigator": principal_investigator,
        "data_steward": data_steward,
    }

    return output
