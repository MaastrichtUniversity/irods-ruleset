# /rules/tests/run_test.sh -r get_all_users_id -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_users_id(ctx):
    """
    Query all the (authorized) projects sizes in one query.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    Dict
        Key => project id; Value => Project size
    """

    project = {}

    for account in row_iterator("USER_ID", "", AS_LIST, ctx.callback):
        project[account[0]] = account[0]

    return project
