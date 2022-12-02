# /rules/tests/run_test.sh -r get_project_user_members -a "P000000015" -j
import json

from datahubirodsruleset.core import make, Output, TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_user_members(ctx, project_id):
    """
    Get the list of all users with at least read access to the input project.
    If a group is part of the project ACL, its members are added to the output list.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010

    Returns
    -------
    dict
        * users: list
        * user_display_names: list
        * group_display_names: list
    """
    show_service_accounts = "false"
    users = set()

    # Get all project users with at least viewing:read access
    ret = ctx.callback.list_project_viewers(project_id, TRUE_AS_STRING, show_service_accounts, "")["arguments"][3]
    project = json.loads(ret)
    users.update(project["users"])
    groups = project["groups"]

    group_display_names = [group_object["displayName"] for group_object in project["groupObjects"]]
    user_display_names = [user_object["displayName"] for user_object in project["userObjects"]]
    user_display_names = set(user_display_names)

    # Go over all groups and list their members
    for group_name in groups:
        group_members_info = json.loads(ctx.callback.get_group_members(group_name, "")["arguments"][1])
        users.update(group_members_info["users"])
        user_display_names.update(group_members_info["user_display_names"])

    output = {
        "users": list(users),
        "user_display_names": list(user_display_names),
        "group_display_names": group_display_names,
    }
    return output
