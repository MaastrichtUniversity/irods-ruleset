@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def list_project_managers(ctx, project_id, show_service_accounts):
    """
    Get the project's users with 'own' access right

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
        a json with the lists of groups and users
    """
    groups = []
    users = []

    group_objects = []
    user_objects = []

    for result in row_iterator("COLL_ACCESS_USER_ID",
                               "COLL_ACCESS_NAME = 'own' AND "
                               "COLL_NAME = '/nlmumc/projects/{}'".format(project_id),
                               AS_LIST,
                               ctx.callback):

        account_id = result[0]
        for account in row_iterator("USER_NAME, USER_TYPE",
                                   "USER_ID = '{}'".format(account_id),
                                   AS_LIST,
                                   ctx.callback):
            account_name = account[0]
            account_type = account[1]
            display_name = account_name
            description = ""

            if account_type == "rodsgroup":
                for group_result in row_iterator("META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
                                         "USER_TYPE = 'rodsgroup' AND "
                                         "USER_GROUP_ID = '{}'".format(account_id),
                                         AS_LIST,
                                         ctx.callback):

                    if "displayName" == group_result[0]:
                        display_name = group_result[1]

                    elif "description" == group_result[0]:
                        description = group_result[1]

                groups.append(account_name)
                group_object = {
                    "groupName": account_name, "groupId": account_id,
                    "displayName": display_name, "description": description
                }
                group_objects.append(group_object)

            if account_type == "rodsuser":
                # Filter out service account from output
                if show_service_accounts == "false" and "service-" in account_name:
                    continue

                for user_result in row_iterator("META_USER_ATTR_VALUE",
                                           "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(account_name),
                                           AS_LIST,
                                           ctx.callback):

                    display_name = user_result[0]

                users.append(account_name)
                user_object = {"userName": account_name, "userId": account_id, "displayName": display_name}
                user_objects.append(user_object)

    return {"users": users, "groups": groups, "groupObjects": group_objects, "userObjects": user_objects}
