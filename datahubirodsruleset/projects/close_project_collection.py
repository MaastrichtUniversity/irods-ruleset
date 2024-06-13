# /rules/tests/run_test.sh -r close_project_collection -a "P000000010,C000000001"
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path, format_project_collection_path


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def close_project_collection(ctx, project_id, collection_id):
    """
    Get the project's users with 'own' access right
    Is always run by 'rodsadmin' accounts

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010
    collection_id: str
        The collection's id; e.g: C000000001

    Returns
    -------
    dict
        a json with the lists of groups and users
    """
    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    project_path = format_project_path(ctx, project_id)

    for result in row_iterator(
        "DATA_ACCESS_USER_ID",
        f"COLL_NAME = '{project_collection_path}' AND DATA_NAME = 'instance.json'",
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]
        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            # Remove permissions for all users on the PC that have access on the instance.json 
            # This is to mitigate an issue where individual users, that are part of a group, still have own access on their 
            # individual account
            ctx.callback.msiSetACL("recursive", "admin:null", account[0], project_collection_path)

    for result in row_iterator(
        "COLL_ACCESS_USER_ID",
        f"COLL_NAME = '{project_path}'",
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]
        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            # Add back read permissions for all users that have rights on the project.
            ctx.callback.msiSetACL("recursive", "admin:read", account[0], project_collection_path)
