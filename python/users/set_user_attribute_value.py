# /rules/tests/run_test.sh -r set_user_attribute_value -a "jmelius,foo,bar"

@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def set_user_attribute_value(ctx, username, attribute, value):
    """
    Set an attribute value to the input user

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username : str
        The username
    attribute : str
        The user attribute to set
    value : str
        The user attribute's value to set
    """
    kvp = ctx.callback.msiString2KeyValPair("{}={}".format(attribute, value), irods_types.BytesBuf())["arguments"][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, username, "-u")
    ctx.callback.msiWriteRodsLog("INFO: {}: Setting '{}' to '{}'".format(username, attribute, value), 0)
