# /rules/tests/run_test.sh -r list_contributing_projects -a "false" -j -u jmelius
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output

# Bound GenQuery IN conditions, including catalogs with 19-digit IDs.
_QUERY_BATCH_SIZE = 20


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_contributing_projects(ctx, show_service_accounts):
    """
    Query the list of ACL for all projects for the client user.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        All projects for which the user is a contributor. Per project, it displays:
          - project ID
          - project metadata (from AVUs)
          - project ACL (managers, contributors, viewers);
    """
    username = ctx.callback.get_client_username("")["arguments"][0]
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    groups = ",".join(
        f"'{int(group_id)}'"
        for group_id, in row_iterator("USER_GROUP_ID", f"USER_ID = '{user_id}'", AS_LIST, ctx.callback)
    )
    if not groups:
        return []

    # Preserve the contributor/manager visibility filter before fetching any
    # metadata or ACLs. All queries use the caller's normal permissions.
    conditions = (
        f"COLL_ACCESS_NAME in ('own', 'modify_object') and COLL_ACCESS_USER_ID in ({groups}) and COLL_PARENT_NAME = '/nlmumc/projects'"
    )
    projects = {}
    for catalog_id, project_path in row_iterator("COLL_ID, order(COLL_NAME)", conditions, AS_LIST, ctx.callback):
        project = {"id": formatters.get_project_id_from_project_path(project_path)}
        for role in ("contributors", "managers", "viewers"):
            project[role] = {"users": [], "groups": [], "groupObjects": [], "userObjects": []}
        projects[catalog_id] = project

    if not projects:
        return []

    attributes = (ProjectAVUs.TITLE.value, ProjectAVUs.RESOURCE.value, ProjectAVUs.COLLECTION_METADATA_SCHEMAS.value)
    attribute_names = ",".join(f"'{attribute}'" for attribute in attributes)
    project_ids = list(projects)
    acl_entries = []
    for offset in range(0, len(project_ids), _QUERY_BATCH_SIZE):
        ids = ",".join(f"'{int(identifier)}'" for identifier in project_ids[offset : offset + _QUERY_BATCH_SIZE])
        condition = f"COLL_ID in ({ids})"
        # Query metadata and ACLs separately, so their rows do not multiply.
        for catalog_id, attribute, value in row_iterator(
            "COLL_ID, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            condition + f" AND META_COLL_ATTR_NAME in ({attribute_names})",
            AS_LIST,
            ctx.callback,
        ):
            projects[catalog_id][attribute] = value

        acl_entries.extend(row_iterator(
            "COLL_ID, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
            condition + " AND COLL_ACCESS_NAME in ('own','modify_object','read_object')",
            AS_LIST,
            ctx.callback,
        ))

    for project in projects.values():
        for attribute in attributes:
            if project.get(attribute, "") == "":
                ctx.callback.msiExit(
                    "-1", f"ERROR: The attribute '{attribute}' of collection '/nlmumc/projects/{project['id']}' has no value in iCAT"
                )

    # Resolve each distinct account once per call, even if it occurs in many
    # projects. Keep identities separate from AVUs to include metadata-less users.
    account_ids = list(dict.fromkeys(entry[1] for entry in acl_entries))
    accounts = {}
    show_service_accounts = formatters.format_string_to_boolean(show_service_accounts)
    for offset in range(0, len(account_ids), _QUERY_BATCH_SIZE):
        ids = ",".join(f"'{int(identifier)}'" for identifier in account_ids[offset : offset + _QUERY_BATCH_SIZE])
        for account_id, name, account_type in row_iterator(
            "USER_ID, USER_NAME, USER_TYPE", f"USER_ID in ({ids})", AS_LIST, ctx.callback
        ):
            if account_type not in ("rodsuser", "rodsgroup"):
                continue
            if account_type == "rodsuser" and not show_service_accounts and "service-" in name:
                continue
            accounts[account_id] = {"name": name, "type": account_type, "displayName": name, "description": ""}

    account_ids = list(accounts)
    for offset in range(0, len(account_ids), _QUERY_BATCH_SIZE):
        ids = ",".join(f"'{int(identifier)}'" for identifier in account_ids[offset : offset + _QUERY_BATCH_SIZE])
        for account_id, attribute, value in row_iterator(
            "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
            f"USER_ID in ({ids}) AND META_USER_ATTR_NAME in ('displayName','description')",
            AS_LIST,
            ctx.callback,
        ):
            accounts[account_id][attribute] = value

    roles = {"own": "managers", "modify_object": "contributors", "read_object": "viewers"}
    for catalog_id, account_id, access in acl_entries:
        account = accounts.get(account_id)
        if account is None:
            continue
        role = projects[catalog_id][roles[access]]
        if account["type"] == "rodsgroup":
            role["groups"].append(account["name"])
            role["groupObjects"].append({
                "groupName": account["name"], "groupId": account_id,
                "displayName": account["displayName"], "description": account["description"],
            })
        else:
            role["users"].append(account["name"])
            role["userObjects"].append({
                "userName": account["name"], "userId": account_id, "displayName": account["displayName"],
            })

    return list(projects.values())
