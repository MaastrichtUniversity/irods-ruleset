@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_internal_affiliation_status(ctx, username):
    """
    Get the user voPersonExternalID and check if the user is part of the UM or MUMC organization.

    Parameters
    ----------
    ctx
    username: str
        The user to check

    Returns
    -------
    bool
        True, if the user is from the UM or MUMC organization. Otherwise, False.
    """
    ret = ctx.get_user_attribute_value(username, "voPersonExternalID", TRUE_AS_STRING, "result")["arguments"][3]
    external_id = json.loads(ret)["value"]
    affiliation = external_id.split("@")[1]
    ctx.writeLine("stdout", affiliation)
    if affiliation in ["unimaas.nl", "mumc.nl"]:
        return True
    return False
