# /rules/tests/run_test.sh -r get_users_active_permissions -a "dlinssen" -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_users_active_permissions(ctx, username):
    """
    Returns all of the users current permissions on projects

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username:
        The username of the user to check

    Returns
    -------
    Dict
    """
    acls = []

    # Check if the user exists
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    if not user_id:
        ctx.callback.msiExit("-1", "Username {} does not exist".format(username))

    # Get the ACLs
    for acl in row_iterator("COLL_NAME, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME", "COLL_PARENT_NAME = '/nlmumc/projects' AND COLL_ACCESS_USER_ID = '{}'".format(user_id), AS_LIST, ctx.callback):
        acls.append(
        {
            "project": acl[0],
            "username": username,
            "user_id": acl[1],
            "access": acl[2]
        })

    return acls