@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_contributing_project(ctx, show_service_accounts):
    """
    Query the list of ACL for a project for the client user

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        The list of usernames for managers, contributors and viewers.
        Returns an empty list if the user is not a contributor.
    """
    projects = []
    groups = ""
    username = ctx.callback.get_client_username('')["arguments"][0]

    ret = ctx.callback.userNameToUserId(username, "*userId")
    user_id = ret["arguments"][1]

    for result in row_iterator("USER_GROUP_ID",
                                  "USER_ID = '{}'".format(user_id),
                                  AS_LIST,
                                  ctx.callback):
        group_id = "'" + result[0] + "'"
        groups = groups + "," + group_id

    # Remove first comma
    groups = groups[1:]

    # Get the collection size on each resources
    parameters = "COLL_NAME"
    conditions = "COLL_ACCESS_NAME in ('own', 'modify object') " \
                 "and COLL_ACCESS_USER_ID in ({}) " \
                 "and COLL_PARENT_NAME = '/nlmumc/projects'".format(groups)

    for collection_result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        project = {"id": collection_result[0].split("/")[3]}

        # List Contributors
        ret = ctx.callback.listProjectContributors(project["id"], "false", "")["arguments"][2]
        project["contributors"] = json.loads(ret)

        # List Managers
        ret = ctx.callback.list_project_managers(project["id"], show_service_accounts, "")["arguments"][2]
        project["managers"] = json.loads(ret)

        # List Viewers
        ret = ctx.callback.listProjectViewers(project["id"], "false", "")["arguments"][2]
        project["viewers"] = json.loads(ret)

        # Get project metadata
        # Note: Retrieving the rule outcome is done with '["arguments"][2]'
        project["title"] = ctx.callback.getCollectionAVU(collection_result[0], "title", "", "", "true")["arguments"][2]
        project["resource"] = ctx.callback.getCollectionAVU(collection_result[0], "resource", "", "", "true")["arguments"][2]

        projects.append(project)

    return projects
