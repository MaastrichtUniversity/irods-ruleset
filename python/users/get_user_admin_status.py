# /rules/tests/run_test.sh -r get_user_admin_status -a "jmelius" -j
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_admin_status(ctx, username):
    """
    Returns if the user is part of the admin-group or not

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    username : str
        The username

    Returns
    -------
    str
        True or false as a string
    """

    groups = json.loads(ctx.callback.get_user_group_memberships(TRUE_AS_STRING, username, "")["arguments"][2])
    is_admin = False
    for group in groups:
        if group["name"] == "DH-project-admins":
            is_admin = True
            break

    return is_admin
