@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_username_attribute_value(ctx, username, attribute):
    """
    Query an attribute value from the user list of AVU

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    username : str
        The username
    attribute : str
        The user attribute to query

    Returns
    -------
    dict
        The attribute value
    """
    value = ""
    for result in row_iterator("META_USER_ATTR_VALUE",
                               "USER_NAME = '{}' AND META_USER_ATTR_NAME = '{}'".format(username, attribute),
                               AS_LIST,
                               ctx.callback):

        value = result[0]
        
    return {"value": value}
