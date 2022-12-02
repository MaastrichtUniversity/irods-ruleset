# /rules/tests/run_test.sh -r list_contributing_projects -a "false" -j -u jmelius
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING


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
    projects = []
    groups = ""
    username = ctx.callback.get_client_username("")["arguments"][0]
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]

    for result in row_iterator("USER_GROUP_ID", "USER_ID = '{}'".format(user_id), AS_LIST, ctx.callback):
        group_id = "'" + result[0] + "'"
        groups = groups + "," + group_id

    # Remove first comma
    groups = groups[1:]

    # Get the collection size on each resources
    parameters = "COLL_NAME"
    conditions = (
        "COLL_ACCESS_NAME in ('own', 'modify object') "
        "and COLL_ACCESS_USER_ID in ({}) "
        "and COLL_PARENT_NAME = '/nlmumc/projects'".format(groups)
    )

    for project_path in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        project = {"id": formatters.get_project_id_from_project_path(project_path[0])}

        # List Contributors
        ret = ctx.callback.list_project_contributors(project["id"], FALSE_AS_STRING, show_service_accounts, "")["arguments"][3]
        project["contributors"] = json.loads(ret)

        # List Managers
        ret = ctx.callback.list_project_managers(project["id"], show_service_accounts, "")["arguments"][2]
        project["managers"] = json.loads(ret)

        # List Viewers
        ret = ctx.callback.list_project_viewers(project["id"], FALSE_AS_STRING, show_service_accounts, "")["arguments"][3]
        project["viewers"] = json.loads(ret)

        # Get project metadata
        # Note: Retrieving the rule outcome is done with '["arguments"][2]'
        project[ProjectAVUs.TITLE.value] = ctx.callback.getCollectionAVU(
            project_path[0], ProjectAVUs.TITLE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        project[ProjectAVUs.RESOURCE.value] = ctx.callback.getCollectionAVU(
            project_path[0], ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        project[ProjectAVUs.COLLECTION_METADATA_SCHEMAS.value] = ctx.callback.getCollectionAVU(
            project_path[0], ProjectAVUs.COLLECTION_METADATA_SCHEMAS.value, "", "", TRUE_AS_STRING
        )["arguments"][2]

        projects.append(project)

    return projects
