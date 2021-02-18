@make(inputs=range(4), outputs=[], handler=Output.STORE)
def set_acl(ctx, mode, access, user, path):
    """
    Set the ACL of a given collection

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    mode : str
        'default', 'recursive' excepted values
    access : str
        access level: 'own', 'write', 'read'
    user : str
        The username
    path : str
        The absolute path of the collection
    """
    ctx.callback.msiSetACL(mode, access, user, path)

