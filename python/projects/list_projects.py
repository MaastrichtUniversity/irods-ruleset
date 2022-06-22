# /rules/tests/run_test.sh -r list_projects -a "false"
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_projects(ctx, show_service_accounts):
    """
    Get a listing of all (authorized) projects

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    list
        a json list of projects objects
    """

    # Initialize the projects listing
    projects = []
    output = {"has_financial_view_access": False}

    # Loop over all projects
    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback):

        # Get all the project's avu
        ret = ctx.callback.get_project_details(result[0], show_service_accounts, "")["arguments"][2]
        project = json.loads(ret)

        # Check if the client user has at least financial view access for one project
        if not output["has_financial_view_access"] and project["has_financial_view_access"]:
            output = {"has_financial_view_access": project["has_financial_view_access"]}

        # Append this project to the list
        projects.append(project)

    # Append this projects list to the rule output
    output["projects"] = projects

    # return projects listing
    return output
