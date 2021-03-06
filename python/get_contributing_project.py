@make(inputs=[0,1], outputs=[2], handler=Output.STORE)
def get_contributing_project(ctx, project_id, show_service_accounts):
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
        Get a project if the user if the user is a contributor. Tt displays:
          - project ID
          - project metadata (from AVUs)
          - project ACL (managers, contributors, viewers);
    """
    project = {}
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
                 "and COLL_NAME = '/nlmumc/projects/{}'".format(groups, project_id)

    for collection_result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        project = {"id": collection_result[0].split("/")[3]}

        # List Managers
        ret = ctx.callback.list_project_managers(project["id"], show_service_accounts, "")["arguments"][2]
        project["managers"] = json.loads(ret)

        # List Contributors
        ret = ctx.callback.list_project_contributors(project["id"], "false", show_service_accounts, "")["arguments"][3]
        project["contributors"] = json.loads(ret)

        # List Viewers
        ret = ctx.callback.list_project_viewers(project["id"], "false", show_service_accounts, "")["arguments"][3]
        project["viewers"] = json.loads(ret)

        project["title"] = ctx.callback.getCollectionAVU(collection_result[0], "title", "", "", "true")["arguments"][2]
        project["resource"] = ctx.callback.getCollectionAVU(collection_result[0], "resource", "", "", "true")["arguments"][2]

    return project
