# /rules/tests/run_test.sh -r get_all_users_groups_memberships -a "false,false,false,false" -j

@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def get_all_users_groups_memberships(
    ctx, show_service_accounts, show_special_groups, show_username, extended_group_info
):
    """
    Query the group memberships all existing users with some extra information based on the input parameters.

    Parameters
    ----------
    ctx
    show_service_accounts: bool
        include service accounts in the output
    show_special_groups: bool
        include special groups in the output
    show_username: bool
        include user_names in output
    extended_group_info: bool
        include extended group information in the output

    Returns
    -------
    dict
        With key for every userId and for every userId the groups where it belongs to.

    """
    ret = ctx.callback.getUsers(show_service_accounts, "")["arguments"][1]
    users = json.loads(ret)
    output = {}

    for user in users:
        output[user["userId"]] = {}
        ret = ctx.callback.get_user_group_memberships(show_special_groups, user["userName"], "")["arguments"][2]
        groups = json.loads(ret)
        if extended_group_info == TRUE_AS_STRING:
            output[user["userId"]]["groups"] = groups
            output[user["userId"]]["group_names"] = []
            for group in groups:
                output[user["userId"]]["group_names"].append(group["name"])
        else:
            output[user["userId"]]["groups"] = []
            output[user["userId"]]["group_names"] = []
            for group in groups:
                output[user["userId"]]["group_names"].append(group["name"])
        if show_username == TRUE_AS_STRING:
            output[user["userId"]]["user_name"] = user["userName"]
        else:
            output[user["userId"]]["user_name"] = None

    return output
