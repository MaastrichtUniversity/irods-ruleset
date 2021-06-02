@make(inputs=[], outputs=[0], handler=Output.STORE)
def optimized_list_projects(ctx):
    """
    Optimize the query to get a listing of all (authorized) projects.
    The code aim to have better performance instead of being reusable.
    The rule returns all the project's AVUs, the project's size and for the ACL only the ACCESS_USER_ID.
    To retrieve the username, display name, etc.. of a user, we need to use get_user_or_group_by_id().
    The result of get_user_or_group_by_id is intended to be cached by the iRODS client.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    list
        a json list of projects objects
    """

    output = []

    project = reset_project_dict()

    previous_project_flag = ""

    # Query all the projects size in one query
    ret = ctx.callback.get_projects_size("")["arguments"][0]
    sizes = json.loads(ret)

    # Query the service accounts to filter out of the output
    ret = ctx.callback.get_service_accounts_id("")["arguments"][0]
    filter = json.loads(ret)

    # Query all the current existing users id.
    # This is needed because of phantom COLL_ACCESS_USER_ID
    # => when deleted users appear in the ACL
    ret = ctx.callback.get_all_users_id("")["arguments"][0]
    users_id = json.loads(ret)

    for result in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
                               "COLL_PARENT_NAME = '/nlmumc/projects'",
                               AS_LIST,
                               ctx.callback):
        project_path = result[0]
        attribute_name = result[1]
        attribute_value = result[2]
        access_user_id = result[3]
        access_level_name = result[4]
        if previous_project_flag == project_path:
            project[attribute_name] = attribute_value

            if access_user_id not in filter and access_user_id in users_id:
                add_access_id_to_project(access_user_id, access_level_name, project)
        else:
            project = reset_project_dict()
            project["path"] = project_path.split("/")[3]

            # Calculate the project's size
            if project["path"] in sizes:
                project["dataSizeGiB"] = sizes[project["path"]]
            else:
                project["dataSizeGiB"] = float(0)

            output.append(project)

        previous_project_flag = project_path

    return output


def add_access_id_to_project(access_id, access_name, project):
    role = map_access_level_name_to_role(access_name)
    if access_id not in project[role]:
        project[role].append(access_id)


def map_access_level_name_to_role(access):
    role = ""
    if access == "own":
        role = "managers"
    elif access == "modify object":
        role = "contributors"
    elif access == "read object":
        role = "viewers"

    return role


def reset_project_dict():
    project = {
        "managers":  [],
        "contributors": [],
        "viewers":  [],
    }
    return project
