@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_users_id(ctx):
    """
    Query all the (authorized) projects sizes in one query.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    Dict
        Key => project id; Value => Project size
    """

    project = {}

    for account in row_iterator("USER_ID",
                                "",
                                AS_LIST,
                                ctx.callback):
        project[account[0]] = account[0]

    return project
