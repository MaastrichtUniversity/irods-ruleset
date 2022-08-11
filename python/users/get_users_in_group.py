# /rules/tests/run_test.sh -r get_users_in_group -a "datahub"
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_users_in_group(ctx, group_name):

    users = []
    for result in row_iterator(
        "USER_NAME", "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsuser'".format(group_name), AS_LIST, ctx.callback
    ):
        if group_name != result[0]:
            users.append(result[0])

    return users
