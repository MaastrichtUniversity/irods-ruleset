# /rules/tests/run_test.sh -r get_service_accounts_id -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_service_accounts_id(ctx):
    """
    Query the ids of rods and service accounts

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    List[str]
        List of the service accounts ids
    """

    output = []

    for account in row_iterator("USER_ID", "USER_NAME = 'rods'", AS_LIST, ctx.callback):
        output.append(account[0])

    for account in row_iterator("USER_ID", "USER_NAME like 'service-%'", AS_LIST, ctx.callback):
        output.append(account[0])

    return output
