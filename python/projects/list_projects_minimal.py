# /rules/tests/run_test.sh -r list_projects_minimal
@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_projects_minimal(ctx):
    """
    Get a listing of all (authorized) projects

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    list
        a json list of projects objects
    """

    # Initialize the projects listing
    projects = []

    # Loop over all projects
    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback):
        project = {
            "id": formatters.get_project_id_from_project_path(result[0]),
            "title": ctx.getCollectionAVU(result[0], "title", "", "", TRUE_AS_STRING)["arguments"][2]
        }

        # Append this project to the list
        projects.append(project)

    # return projects listing
    return projects
