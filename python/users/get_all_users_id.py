# /rules/tests/run_test.sh -r get_all_users_id -j

@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_users_id(ctx):
    """
    Query all the existing users in iRODS.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    Dict
        Key => user id; Value => user id
    """

    users = {}

    for account in row_iterator("USER_ID", "", AS_LIST, ctx.callback):
        users[account[0]] = account[0]

    return users
