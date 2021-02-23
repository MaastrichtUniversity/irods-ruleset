import unicodedata


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_managing_project(ctx, project_id):
    """
    Query the list of ACL for a project for the client user

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id : str
        The project's id; eg.g P000000010

    Returns
    -------
    dict
        The list of usernames for managers, contributors and viewers.
        Returns an empty list if the user is not a manager.
    """

    # Get the client username
    username = ''
    var_map = session_vars.get_map(ctx.rei)
    user_type = 'client_user'
    userrec = var_map.get(user_type, '')
    if userrec:
        username = userrec.get('user_name', '')

    result = ctx.callback.listProjectManagers(project_id, "managers")
    managers = result["arguments"][1].decode('utf-8')
    # Remove unicode 'u' from the string result
    managers = "".join(ch for ch in managers if unicodedata.category(ch)[0] != "C")
    managers = json.loads(managers)

    # if the user is not part of the managers, return an empty list
    if username not in managers['users']:
        return []

    result = ctx.callback.listProjectContributors(project_id, 'false', "contributors")
    contributors = result["arguments"][2]
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
