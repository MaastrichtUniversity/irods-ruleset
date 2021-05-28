@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_or_group_by_id(ctx, account_id):
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

    # output = {"result": None}
    output = ""

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
                                             "USER_TYPE = 'rodsgroup' AND USER_GROUP_ID = '{}'".format(account_id),
                                             AS_LIST,
                                             ctx.callback):

                if "displayName" == group_result[0]:
                    display_name = group_result[1]

                elif "description" == group_result[0]:
                    description = group_result[1]

            group_object = {
                "groupName": account_name, "groupId": account_id,
                "displayName": display_name, "description": description,
                "account_type": account_type
            }
            output = group_object

        if account_type == "rodsuser":
            # Filter out service account from output
            if "service-" in account_name:
                continue

            for user_result in row_iterator("META_USER_ATTR_VALUE",
                                            "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(account_name),
                                            AS_LIST,
                                            ctx.callback):

                display_name = user_result[0]

            user_object = {
                "userName": account_name, "userId": account_id,
                "displayName": display_name, "account_type": account_type
            }
            output = user_object

    return output
