@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_service_accounts_id(ctx):
    """
    Query the hard-coded list of rods and service accounts ids

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    List[str]
        List of the service accounts ids
    """

    output = []
    names = "'rods', 'service-dropzones', 'service-mdl', 'service-pid', 'service-disqover', 'service-surfarchive'"

    for account in row_iterator("USER_ID",
                                "USER_NAME in ({})".format(names),
                                AS_LIST,
                                ctx.callback):
        output.append(account[0])

    return output
