# /rules/tests/run_test.sh -r get_project_user_members -a "P000000015" -u service-disqover -j
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
    users.update(json.loads(ret)["users"])
    groups = json.loads(ret)["groups"]

    # Go over all groups and list their members
    for group in groups:
        group_users = json.loads(ctx.callback.get_group_members(group, "")["arguments"][1])
        users.update(group_users)

    return list(users)
