# /rules/tests/run_test.sh -r get_groups -a "false" -j
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_groups(ctx, show_special_groups):
    """
    Get a listing of the all project's collections

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    show_special_groups: str
        'true'/'false' expected; If true, hide the special groups in the result

    Returns
    -------
    list
        a json list of collections objects
    """
    groups = {}
    for name, group_id in row_iterator("USER_NAME, USER_ID", "USER_TYPE = 'rodsgroup'", AS_LIST, ctx.callback):
        if not formatters.format_string_to_boolean(show_special_groups) and name in (
            "public", "rodsadmin", "DH-ingest", "DH-project-admins"
        ):
            continue
        groups[group_id] = {"name": name, "groupId": group_id, "displayName": name, "description": ""}
    if groups:
        for group_id, attribute, value in row_iterator(
            "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
            "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME in ('displayName','description')",
            AS_LIST,
            ctx.callback,
        ):
            if group_id in groups:
                groups[group_id][attribute] = value
    return list(groups.values())
