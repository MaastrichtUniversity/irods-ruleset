@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_projects_finance(ctx):
    """
    Query the list of projects financial information, if the client user is a PI or data steward

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    dict
        The list of the projects financial information
    """

    # Get the client username
    username = ''
    var_map = session_vars.get_map(ctx.rei)
    user_type = 'client_user'
    userrec = var_map.get(user_type, '')
    if userrec:
        username = userrec.get('user_name', '')
    
    condition = "COLL_PARENT_NAME = '/nlmumc/projects' AND META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}'"

    projects = []
    # Get all the projects where the user is the principal investigator
    for result in row_iterator("COLL_NAME", condition.format('OBI:0000103', username), AS_LIST, ctx.callback):
        projects.append(result[0])

    # Get all the projects where the user is the data steward
    for result in row_iterator("COLL_NAME", condition.format('dataSteward', username), AS_LIST, ctx.callback):
        projects.append(result[0])

    output = []
    # Loop over the unique set of projects to avoid duplicate query/values
    for project in set(projects):
        # Get project AVUs budget_number & title
        budget_number = ctx.callback.getCollectionAVU(project, "responsibleCostCenter", "", "", "true")["arguments"][2]
        title = ctx.callback.getCollectionAVU(project, "title", "", "", "true")["arguments"][2]

        # Get project finance information
        ret = ctx.callback.get_project_finance(project, "result")
        ret = json.loads(ret["arguments"][1])

        # Add the AVUs value to the project dictionary
        ret["project_id"] = project.split("/")[3]
        ret["budget_number"] = budget_number
        ret["title"] = title
        output.append(ret)

    return output
