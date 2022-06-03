# /rules/tests/run_test.sh -r get_user_group_memberships -a "false,pvanschay2" -j

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_user_group_memberships(ctx, show_special_groups, username):
    """
    Get the group membership of a given user

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    show_special_groups : str
        'true'/'false' expected values; If true, hide the special groups in the result
    username : str
        The username to use for the query

    Returns
    -------
    list
        a json list of groups objects
    """
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    output = []

    for result in row_iterator(
        "order(USER_GROUP_NAME), USER_GROUP_ID", "USER_ID = '{}'".format(user_id), AS_LIST, ctx.callback
    ):

        group_name = result[0]
        group_id = result[1]
        group_display_name = result[0]
        group_description = ""

        if group_name != username:
            for metadata_result in row_iterator(
                "META_USER_ATTR_NAME, META_USER_ATTR_VALUE, USER_GROUP_ID, USER_GROUP_NAME",
                "USER_TYPE = 'rodsgroup' AND USER_GROUP_ID = '{}'".format(group_id),
                AS_LIST,
                ctx.callback,
            ):

                if "displayName" == metadata_result[0]:
                    group_display_name = metadata_result[1]

                elif "description" == metadata_result[0]:
                    group_description = metadata_result[1]

            group_object = {
                "groupId": group_id,
                "name": group_name,
                "displayName": group_display_name,
                "description": group_description,
            }

            if not formatters.format_string_to_boolean(show_special_groups):
                if (
                    group_name != "public"
                    and group_name != "rodsadmin"
                    and group_name != "DH-ingest"
                    and group_name != "DH-project-admins"
                ):
                    output.append(group_object)
            else:
                output.append(group_object)

    return output
