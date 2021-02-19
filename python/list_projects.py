@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_projects(ctx):
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
    # Get the client username
    username = ''
    var_map = session_vars.get_map(ctx.rei)
    user_type = 'client_user'
    userrec = var_map.get(user_type, '')
    if userrec:
        username = userrec.get('user_name', '')

    condition = "COLL_PARENT_NAME = '/nlmumc/projects' AND META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}'"

    has_financial_view_access = False
    # Check if the  the user is the principal investigator for one project
    for result in row_iterator("COLL_NAME", condition.format('OBI:0000103', username), AS_LIST, ctx.callback):
        has_financial_view_access = True
        break

    # Only check for data steward if the user is not a PI for any projects
    if not has_financial_view_access:
        # Get all the projects where the user is the data steward
        for result in row_iterator("COLL_NAME", condition.format('dataSteward', username), AS_LIST, ctx.callback):
            has_financial_view_access = True
            break
    output = {"has_financial_view_access": has_financial_view_access}

    # Initialize the projects listing
    projects = []

    # Loop over all projects
    for result in row_iterator("COLL_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               ctx.callback):

        ret = ctx.callback.get_project_details(result[0], '')["arguments"][1]
        project = json.loads(ret)

        # Append this project to the list
        projects.append(project)

    # Append this projects list to the rule output
    output["projects"] = projects

    # return projects listing
    return output
