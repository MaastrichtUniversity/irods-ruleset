# /rules/tests/run_test.sh -r get_all_users_email -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_users_email(ctx):
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

    emails = []

    for email in row_iterator("USER_NAME, META_USER_ATTR_VALUE", "META_USER_ATTR_NAME LIKE 'email'", AS_LIST, ctx.callback):
        if '@' in email[1]:
            emails.append(email[1])

    return emails
