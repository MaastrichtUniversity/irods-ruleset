# /rules/tests/run_test.sh -r get_user_id -a "jmelius" -j

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_id(ctx, username):
    """
    Query the user id based on the input username.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username: str
        The username.

    Returns
    -------
    str
        The user id.
    """
    user_id = ""
    for result in row_iterator("USER_ID", "USER_NAME = '{}'".format(username), AS_LIST, ctx.callback):
        user_id = result[0]
    return user_id
