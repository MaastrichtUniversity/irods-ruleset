# /rules/tests/run_test.sh -r get_project_user_members -a "P000000015" -j
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_user_members(ctx, project_id):
    """
    Get the list of all users with at least read access to the input project.
    If a group is part of the project ACL, its members are added to the output list.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010

    Returns
    -------
    list
        a list usernames
    """
    show_service_accounts = "false"
    users = set()

    # Get all project users with at least viewing:read access
    ret = ctx.callback.list_project_viewers(project_id, TRUE_AS_STRING, show_service_accounts, "")["arguments"][3]
    project = json.loads(ret)
    users.update(project["users"])
    groups = project["groups"]

    group_display_names = [group_object["displayName"] for group_object in project["groupObjects"]]

    # Go over all groups and list their members
    for group_name in groups:
        group_members = json.loads(ctx.callback.get_group_members(group_name, "")["arguments"][1])
        users.update(group_members)

    output = {
        "users": list(users),
        "group_display_names": group_display_names,
    }
    return output
