# /rules/tests/run_test.sh -r get_all_users_with_access_to_project -a "P000000015" -u service-disqover
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_all_users_with_access_to_project(ctx, project_id):
    show_service_accounts = "false"

    users = []
    groups = []

    # List Contributors
    ret = ctx.callback.list_project_contributors(project_id, FALSE_AS_STRING, show_service_accounts, "")["arguments"][3]
    users.extend(json.loads(ret)["users"])
    groups.extend(json.loads(ret)["groups"])

    # List Managers
    ret = ctx.callback.list_project_managers(project_id, show_service_accounts, "")["arguments"][2]
    users.extend(json.loads(ret)["users"])
    groups.extend(json.loads(ret)["groups"])

    # List Viewers
    ret = ctx.callback.list_project_viewers(project_id, FALSE_AS_STRING, show_service_accounts, "")["arguments"][3]
    users.extend(json.loads(ret)["users"])
    groups.extend(json.loads(ret)["groups"])

    # Go over all groups and list their members
    for group in groups:
        group_users = json.loads(ctx.callback.get_users_in_group(group, "")["arguments"][1])
        users.extend(group_users)

    # Remove duplicates
    users = list(dict.fromkeys(users))
    return users
