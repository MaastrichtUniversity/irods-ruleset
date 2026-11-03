# /rules/tests/run_test.sh -r get_user_group_memberships -a "false,pvanschay2" -j

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import in_conditions


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_user_group_memberships(ctx, show_special_groups, username):
    """
    Get the group membership of a given user

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    show_special_groups : str
        'true'/'false' expected values; If true, hide the special groups in the result
    username : str
        The username to use for the query

    Returns
    -------
    list
        a json list of groups objects
    """
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    groups = {}
    for name, group_id in row_iterator(
        "order(USER_GROUP_NAME), USER_GROUP_ID", f"USER_ID = '{user_id}'", AS_LIST, ctx.callback
    ):
        if name == username:
            continue
        if not formatters.format_string_to_boolean(show_special_groups) and name in (
            "public", "rodsadmin", "DH-ingest", "DH-project-admins"
        ):
            continue
        groups[group_id] = {"groupId": group_id, "name": name, "displayName": name, "description": ""}
    for condition in in_conditions("USER_ID", groups):
        for group_id, attribute, value in row_iterator(
            "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
            condition + " AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME in ('displayName','description')",
            AS_LIST, ctx.callback,
        ):
            groups[group_id][attribute] = value
    return list(groups.values())
