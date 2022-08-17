# /rules/tests/run_test.sh -r get_user_or_group_by_id -a "10043"

@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_or_group_by_id(ctx, account_id):
    """
    Get user or group AVUs from its id

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    account_id : str
        The account's id; eg.g '10132'

    Returns
    -------
    dict
        a json with the lists of groups and users
    """

    output = ""

    for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
        account_name = account[0]
        account_type = account[1]
        display_name = account_name
        description = ""

        if account_type == "rodsgroup":
            for group_result in row_iterator(
                "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
                "USER_TYPE = 'rodsgroup' AND USER_GROUP_ID = '{}'".format(account_id),
                AS_LIST,
                ctx.callback,
            ):

                if "displayName" == group_result[0]:
                    display_name = group_result[1]

                elif "description" == group_result[0]:
                    description = group_result[1]

            group_object = {
                "groupName": account_name,
                "groupId": account_id,
                "displayName": display_name,
                "description": description,
                "account_type": account_type,
            }
            output = group_object

        if account_type == "rodsuser":
            # Filter out service account from output
            if "service-" in account_name:
                continue

            for user_result in row_iterator(
                "META_USER_ATTR_VALUE",
                "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(account_name),
                AS_LIST,
                ctx.callback,
            ):

                display_name = user_result[0]

            user_object = {
                "userName": account_name,
                "userId": account_id,
                "displayName": display_name,
                "account_type": account_type,
            }
            output = user_object

    return output
