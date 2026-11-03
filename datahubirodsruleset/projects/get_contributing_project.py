# /rules/tests/run_test.sh -r get_contributing_project -a "P000000010,false" -j -u psuppers
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.listing_queries import avu, collection_metadata, project_roles, query_value


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_contributing_project(ctx, project_id, show_service_accounts):
    """
    Query the list of ACL for a project for the client user.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010.
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result.

    Returns
    -------
    dict
        Get a project if the user is a contributor. It displays:
          - project ID
          - project metadata (from AVUs)
          - project ACL (managers, contributors, viewers);
    """
    project = {}
    groups = ""
    username = ctx.callback.get_client_username("")["arguments"][0]
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]

    for result in row_iterator("USER_GROUP_ID", f"USER_ID = '{user_id}'", AS_LIST, ctx.callback):
        group_id = "'" + result[0] + "'"
        groups = groups + "," + group_id

    # Remove first comma
    groups = groups[1:]

    # Get the collection size on each resources
    parameters = "COLL_NAME"
    conditions = (
        f"COLL_ACCESS_NAME in ('own', 'modify_object') and COLL_ACCESS_USER_ID in ({groups}) and COLL_NAME = '{format_project_path(ctx, project_id)}'"
    )

    for collection_result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        project = {"id": formatters.get_project_id_from_project_path(collection_result[0])}

        roles = project_roles(ctx, collection_result[0], formatters.format_string_to_boolean(show_service_accounts))
        project["managers"] = roles["own"]
        project["contributors"] = roles["modify_object"]
        project["viewers"] = roles["read_object"]
        metadata = collection_metadata(ctx, f"COLL_NAME = {query_value(collection_result[0])}")
        for attribute in (ProjectAVUs.TITLE.value, ProjectAVUs.RESOURCE.value, ProjectAVUs.COLLECTION_METADATA_SCHEMAS.value):
            project[attribute] = avu(ctx, metadata, collection_result[0], attribute, fatal=True)
    return project
