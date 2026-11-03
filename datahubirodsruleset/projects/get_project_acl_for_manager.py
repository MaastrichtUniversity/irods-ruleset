# /rules/tests/run_test.sh -r get_project_acl_for_manager -a "P000000014,false" -u opalmen -j
import json
from dhpythonirodsutils.enums import ProjectAVUs

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.utils import FALSE_AS_STRING
from datahubirodsruleset.listing_queries import avu, collection_metadata, query_value


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_acl_for_manager(ctx, project_id, show_service_accounts):
    """
    Query the list of ACL for a project for the client user

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        The list of usernames for managers, contributors and viewers.
        Returns an empty list if the user is not a manager.
    """
    username = ctx.callback.get_client_username("")["arguments"][0]

    managers = ctx.callback.list_project_managers(project_id, show_service_accounts, "managers")["arguments"][2]
    managers = json.loads(managers)

    # if the user is not part of the managers, return an empty list
    if username not in managers["users"]:
        return []

    contributors = ctx.callback.list_project_contributors(project_id, FALSE_AS_STRING, show_service_accounts, "")[
        "arguments"
    ][3]
    contributors = json.loads(contributors)

    viewers = ctx.callback.list_project_viewers(project_id, FALSE_AS_STRING, show_service_accounts, "viewers")[
        "arguments"
    ][3]
    viewers = json.loads(viewers)

    project_path = format_project_path(ctx, project_id)

    metadata = collection_metadata(ctx, f"COLL_NAME = {query_value(project_path)}")
    principal_investigator = avu(ctx, metadata, project_path, ProjectAVUs.PRINCIPAL_INVESTIGATOR.value, fatal=True)
    data_steward = avu(ctx, metadata, project_path, ProjectAVUs.DATA_STEWARD.value, fatal=True)

    output = {
        "managers": managers,
        "contributors": contributors,
        "viewers": viewers,
        "principal_investigator": principal_investigator,
        "data_steward": data_steward,
    }

    return output
