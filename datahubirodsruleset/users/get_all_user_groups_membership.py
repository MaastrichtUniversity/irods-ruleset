# /rules/tests/run_test.sh -r get_all_users_groups_memberships -a "false,false,false,false" -j
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING


@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def get_all_users_groups_memberships(
    ctx, show_service_accounts, show_special_groups, show_username, extended_group_info
):
    """
    Query the group memberships all existing users with some extra information based on the input parameters.

    Parameters
    ----------
    ctx
    show_service_accounts: bool
        include service accounts in the output
    show_special_groups: bool
        include special groups in the output
    show_username: bool
        include user_names in output
    extended_group_info: bool
        include extended group information in the output

    Returns
    -------
    dict
        With key for every userId and for every userId the groups where it belongs to.

    """
    users = {}
    output = {}
    for user_id, username in row_iterator("USER_ID, USER_NAME", "USER_TYPE = 'rodsuser'", AS_LIST, ctx.callback):
        if show_service_accounts == FALSE_AS_STRING and username.startswith("service-"):
            continue
        users[user_id] = username
        output[user_id] = {
            "groups": [], "group_names": [],
            "user_name": username if show_username == TRUE_AS_STRING else None,
        }

    if not users:
        return output

    show_special_groups = formatters.format_string_to_boolean(show_special_groups)
    group_objects = {}
    # Keep membership and metadata queries separate to avoid multiplying each
    # membership by every group AVU. Users without metadata remain in output.
    for user_id, group_name, group_id in row_iterator(
        "USER_ID, order(USER_GROUP_NAME), USER_GROUP_ID", "USER_TYPE = 'rodsuser'", AS_LIST, ctx.callback
    ):
        if user_id not in users or group_name == users[user_id]:
            continue
        if not show_special_groups and group_name in ("public", "rodsadmin", "DH-ingest", "DH-project-admins"):
            continue
        output[user_id]["group_names"].append(group_name)
        if extended_group_info == TRUE_AS_STRING:
            if group_id not in group_objects:
                group_objects[group_id] = {
                    "groupId": group_id, "name": group_name, "displayName": group_name, "description": "",
                }
            output[user_id]["groups"].append(group_objects[group_id])

    # Name-only reports do not need group metadata at all.
    if group_objects:
        for group_id, attribute, value in row_iterator(
            "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
            "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME in ('displayName','description')",
            AS_LIST,
            ctx.callback,
        ):
            if group_id in group_objects:
                group_objects[group_id][attribute] = value

    return output
