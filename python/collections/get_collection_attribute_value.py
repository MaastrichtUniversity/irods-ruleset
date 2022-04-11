@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_collection_attribute_value(ctx, irods_collection_path, attribute):
    """
    Query an attribute value for the given iRODS collection path

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    irods_collection_path : str
        The path to an irods collection
    attribute : str
        The user attribute to query

    Returns
    -------
    dict
        The attribute value
    """
    value = ""
    for result in row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}' ".format(irods_collection_path, attribute),
        AS_LIST,
        ctx.callback,
    ):
        value = result[0]

    return {"value": value}
