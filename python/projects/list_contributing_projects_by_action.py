# /rules/tests/run_test.sh -r list_contributing_projects_by_action -a "archive" -j -u jmelius

@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_contributing_projects_by_action(ctx, action):
    """
    Query the list of projects where the client user is at least a contributor and the action feature is enable for
    the project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    action: str
        The action label associated to a project feature AVU ('enableArchive'). e.g: 'archive'

    Returns
    -------
    dict
        Per project, it returns the project: ID, path, and title
    """
    projects = []
    groups = ""
    username = ctx.callback.get_client_username("")["arguments"][0]

    action_to_avu = {
        "archive": "enableArchive",
        "unarchive": "enableUnarchive",
        "publish": "enableOpenAccessExport",
        "browse": ""
    }

    if action not in action_to_avu.keys():
        ctx.callback.msiExit("-1", "ERROR: Action '{}' is not recognize".format(action))

    action_avu = action_to_avu[action]

    for result in row_iterator("USER_GROUP_ID", "USER_NAME = '{}'".format(username), AS_LIST, ctx.callback):
        group_id = "'" + result[0] + "'"
        groups = groups + "," + group_id

    # Remove first comma
    groups = groups[1:]

    if action_avu == "":
        action_condition = ""
    else:
        action_condition = "and META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = 'true'".format(action_avu)

    parameters = "COLL_NAME"
    conditions = (
        "COLL_ACCESS_NAME in ('own', 'modify object') "
        "and COLL_ACCESS_USER_ID in ({}) "
        "and COLL_PARENT_NAME = '/nlmumc/projects' {}".format(groups, action_condition)
    )

    for project_path in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        project = {
            "id": formatters.get_project_id_from_project_path(project_path[0]),
            "path": project_path[0],
            "title": ctx.callback.getCollectionAVU(project_path[0], "title", "", "", TRUE_AS_STRING)["arguments"][2]
        }
        projects.append(project)

    return projects
