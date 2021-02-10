@make(inputs=range(4), outputs=[], handler=Output.STORE)
def set_acl(ctx, mode, access, user, path):
    ctx.callback.msiSetACL(mode, access, user, path)


