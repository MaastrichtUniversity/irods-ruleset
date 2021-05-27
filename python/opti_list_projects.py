@make(inputs=[], outputs=[0], handler=Output.STORE)
def opti(ctx):
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

    output = []

    project = reset_project_dict()

    users_name = {}

    previous_project_flag = ""

    for result in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               ctx.callback):
        if previous_project_flag == result[0]:
            project[result[1]] = result[2]
            account = query_account_info(ctx, result[3], users_name)
            add_account_to_project_acl(ctx, project, result[4], account)
        else:
            project = reset_project_dict()
            project["path"] = result[0]

            # Calculate the project's size
            ret = ctx.callback.get_project_size(project["path"], '')["arguments"][1]
            project["dataSizeGiB"] = json.loads(ret)
            output.append(project)

        previous_project_flag = result[0]

    return output


def query_account_info(ctx, account_id, users_name, count):
    if account_id in users_name:
        return users_name[account_id]

    count += 1
    for result in row_iterator("USER_NAME, USER_TYPE",
                                "USER_ID = '{}'".format(account_id),
                                AS_LIST,
                                ctx.callback):
        account_name = result[0]
        account_type = result[1]
        account = False
        if account_type == "rodsgroup":
            account = query_group(ctx, account_name, account_id)
            account["account_type"] = "rodsgroup"

        if account_type == "rodsuser":
            account = query_user(ctx, account_name, account_id)
            account["account_type"] = "rodsuser"
        # All other cases of objectType, such as "" or "rodsadmin", are skipped

        users_name[account_id] = account

        return account


def add_account_to_project_acl(ctx, project, access, account):
    if account and account["account_type"] == "rodsgroup":
        add_group(project, access, account)
    if account and account["account_type"] == "rodsuser":
        add_user(project, access, account)


def map_acl_to_role(access):
    role = ""
    if access == "own":
        role = "managers"

    if access == "modify object":
        role = "contributors"

    if access == "read object":
        role = "viewers"

    return role


def query_group(ctx, account_name, account_id):
    display_name = account_name
    description = ""
    for group_result in row_iterator("META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
                                     "USER_TYPE = 'rodsgroup' AND USER_GROUP_ID = '{}'".format(account_id),
                                     AS_LIST,
                                     ctx.callback):

        if "displayName" == group_result[0]:
            display_name = group_result[1]

        elif "description" == group_result[0]:
            description = group_result[1]

    account = {
        "name": account_name,
        "id": account_id,
        "display_name": display_name,
        "description": description,
    }

    return account


def add_group(project, access, account):
    role = map_acl_to_role(access)
    if account["name"] not in project[role]["groups"]:
        project[role]["groups"].append(account["name"])
        group_object = {
            "groupName": account["name"], "groupId": account["id"],
            "displayName": account["display_name"], "description": account["description"]
        }
        project[role]["groupObjects"].append(group_object)


def query_user(ctx, account_name, account_id):
    # show_service_accounts = "false"
    show_service_accounts = "true"

    # Filter out service account from output
    if show_service_accounts == "false" and "service-" in account_name:
        return

    display_name = account_name
    for user_result in row_iterator("META_USER_ATTR_VALUE",
                                    "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(
                                        account_name),
                                    AS_LIST,
                                    ctx.callback):
        display_name = user_result[0]

    account = {
        "name": account_name,
        "id": account_id,
        "display_name": display_name,
    }

    return account


def add_user(project, access, account):
    role = map_acl_to_role(access)
    if account["name"] not in project[role]["users"]:
        project[role]["users"].append(account["name"])
        user_object = {"userName": account["name"], "userId": account["id"], "displayName": account["display_name"]}
        project[role]["userObjects"].append(user_object)


def reset_project_dict():
    project = {
        "managers": {
            "groupObjects": [],
            "groups": [],
            "userObjects": [],
            "users": []
        },
        "contributors": {
            "groupObjects": [],
            "groups": [],
            "userObjects": [],
            "users": []
        },
        "viewers": {
            "groupObjects": [],
            "groups": [],
            "userObjects": [],
            "users": []
        }
    }
    return project
