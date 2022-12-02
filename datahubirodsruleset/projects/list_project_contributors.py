# /rules/tests/run_test.sh -r list_project_contributors -a "P000000010,false,false" -j -u jmelius
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def list_project_contributors(ctx, project_id, inherited, show_service_accounts):
    """
    Get the project's users with 'write' access right

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010
    inherited : str
        Role inheritance
        * inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
        * inherited='false' only shows explicit contributors. i.e. A contributor only has 'WRITE' access
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        a json with the lists of groups and users
    """
    groups = []
    users = []

    group_objects = []
    user_objects = []

    if formatters.format_string_to_boolean(inherited):
        criteria = "'own', 'modify object'"
    else:
        criteria = "'modify object'"

    for result in row_iterator(
            "COLL_ACCESS_USER_ID",
            "COLL_ACCESS_NAME in ({}) AND ".format(criteria) + "COLL_NAME = '/nlmumc/projects/{}'".format(project_id),
            AS_LIST,
            ctx.callback,
    ):

        account_id = result[0]
        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            account_type = account[1]
            display_name = account_name
            description = ""

            if account_type == "rodsgroup":
                for group_result in row_iterator(
                        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
                        "USER_TYPE = 'rodsgroup' AND " "USER_GROUP_ID = '{}'".format(account_id),
                        AS_LIST,
                        ctx.callback,
                ):

                    if "displayName" == group_result[0]:
                        display_name = group_result[1]

                    elif "description" == group_result[0]:
                        description = group_result[1]

                groups.append(account_name)
                group_object = {
                    "groupName": account_name,
                    "groupId": account_id,
                    "displayName": display_name,
                    "description": description,
                }
                group_objects.append(group_object)

            if account_type == "rodsuser":
                # Filter out service account from output
                if not formatters.format_string_to_boolean(show_service_accounts) and "service-" in account_name:
                    continue

                for user_result in row_iterator(
                        "META_USER_ATTR_VALUE",
                        "USER_NAME = '{}' AND META_USER_ATTR_NAME = 'displayName'".format(account_name),
                        AS_LIST,
                        ctx.callback,
                ):
                    display_name = user_result[0]

                users.append(account_name)
                user_object = {"userName": account_name, "userId": account_id, "displayName": display_name}
                user_objects.append(user_object)
            # All other cases of objectType, such as "" or "rodsadmin", are skipped

    return {"users": users, "groups": groups, "groupObjects": group_objects, "userObjects": user_objects}
