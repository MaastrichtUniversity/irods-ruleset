# /rules/tests/run_test.sh -r get_user_attribute_value -a "jmelius,email,false" -j

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_user_attribute_value(ctx, username, attribute, fatal):
    """
    Query an attribute value from the user list of AVU

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username : str
        The username
    attribute : str
        The user attribute to query
    fatal : str
        'true'/'false' expected; If true, raise an exception when the query result is empty

    Returns
    -------
    dict
        The attribute value
    """
    value = ""
    for result in row_iterator(
        "META_USER_ATTR_VALUE",
        f"USER_NAME = '{username}' AND META_USER_ATTR_NAME = '{attribute}'",
        AS_LIST,
        ctx.callback,
    ):
        value = result[0]

    if formatters.format_string_to_boolean(fatal) and value == "":
        ctx.callback.msiExit("-807000", f"AVU {attribute} is missing for user {username}")

    return {"value": value}
