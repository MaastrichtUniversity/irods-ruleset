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

    # Initialize the projects listing
    output = []

    # Loop over all projects
    for result in row_iterator("COLL_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               ctx.callback):

        ret = ctx.callback.get_project_details(result[0], '')["arguments"][1]
        project = json.loads(ret)

        # Append this project to the list
        output.append(project)

    # return projects listing
    return output
