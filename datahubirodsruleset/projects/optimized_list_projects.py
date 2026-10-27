# /rules/tests/run_test.sh -r optimized_list_projects -u jmelius -j
import json

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


# Keep GenQuery IN conditions small even for catalog IDs with 19 digits.
_PROJECT_BATCH_SIZE = 20


@make(inputs=[], outputs=[0], handler=Output.STORE)
def optimized_list_projects(ctx):
    """
    Optimize the query to get a listing of all (authorized) projects.
    The code aim to have better performance instead of being reusable.
    The rule returns all the project's AVUs, the project's size and for the ACL only the ACCESS_USER_ID.
    To retrieve the username, display name, etc.. of a user, we need to use get_user_or_group_by_id().
    The result of get_user_or_group_by_id is intended to be cached by the iRODS client.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    list
        a json list of projects objects
    """

    # Let iRODS filter project visibility before fetching metadata or ACLs. This
    # limits the following queries to projects the caller can access; each query
    # still runs with the caller's normal iRODS permissions.
    projects = {}
    for collection_id, project_path in row_iterator(
        "COLL_ID, COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback
    ):
        project = reset_project_dict()
        project["path"] = formatters.get_project_id_from_project_path(project_path)
        project["dataSizeGiB"] = float(0)
        projects[collection_id] = project

    if not projects:
        return []

    sizes = json.loads(ctx.callback.get_projects_size("")["arguments"][0])
    service_accounts = set(json.loads(ctx.callback.get_service_accounts_id("")["arguments"][0]))
    users_id = json.loads(ctx.callback.get_all_users_id("")["arguments"][0])

    # Fetch multiple projects per query to avoid a query per project, while
    # keeping IN conditions bounded for callers who can see many projects.
    collection_ids = list(projects)
    for offset in range(0, len(collection_ids), _PROJECT_BATCH_SIZE):
        batch = collection_ids[offset : offset + _PROJECT_BATCH_SIZE]
        # IDs are catalog integers, so names containing quotes never enter the condition.
        ids = ",".join(f"'{int(collection_id)}'" for collection_id in batch)
        condition = f"COLL_ID in ({ids})"

        # The old query joined every metadata field with every ACL entry. Its
        # production plan repeated permission checks for each combined row.
        # Separate metadata and ACL queries avoid that row multiplication.
        for collection_id, attribute_name, attribute_value in row_iterator(
            "COLL_ID, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE", condition, AS_LIST, ctx.callback
        ):
            projects[collection_id][attribute_name] = attribute_value

        # These ACLs populate the displayed roles; project visibility was already
        # determined by the initial query, so restrict this query to those IDs.
        for collection_id, access_user_id, access_level_name in row_iterator(
            "COLL_ID, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
            condition + " AND COLL_ACCESS_NAME in ('own', 'modify_object', 'read_object')",
            AS_LIST,
            ctx.callback,
        ):
            if access_user_id not in service_accounts and access_user_id in users_id:
                add_access_id_to_project(access_user_id, access_level_name, projects[collection_id])

    for project in projects.values():
        project["dataSizeGiB"] = sizes.get(project["path"], float(0))

    return sorted(projects.values(), key=lambda project: project["path"])


def add_access_id_to_project(access_id, access_name, project):
    role = map_access_level_name_to_role(access_name)
    if access_id not in project[role]:
        project[role].append(access_id)


def map_access_level_name_to_role(access):
    role = ""
    if access == "own":
        role = "managers"
    elif access == "modify_object":
        role = "contributors"
    elif access == "read_object":
        role = "viewers"

    return role


def reset_project_dict():
    project = {
        "managers": [],
        "contributors": [],
        "viewers": [],
    }
    return project
