# /rules/tests/run_test.sh -r get_group_members -a "datahub" -j
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_group_members(ctx, group_name):
    """
    Query all members of a group by its name.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    group_name : str
        e.g: 'datahub', 'public', 'scannexus'

    Returns
    -------
    list
        a list of usernames
    """
    users = []
    for result in row_iterator(
        "USER_NAME", "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsuser'".format(group_name), AS_LIST, ctx.callback
    ):
        if group_name != result[0]:
            users.append(result[0])

    return users
