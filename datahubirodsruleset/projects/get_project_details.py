# /rules/tests/run_test.sh -r get_project_details -a "/nlmumc/projects/P000000014,false" -u dlinssen -j
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING
from datahubirodsruleset.listing_queries import avu, collection_metadata, project_roles, query_value


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_details(ctx, project_path, show_service_accounts):
    """
    Get the all the project's AVU

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        Project absolute path
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    list
        a json list of projects objects
    """
    username = ctx.callback.get_client_username("")["arguments"][0]

    has_financial_view_access = False
    # Initialize the project dictionary
    project = {}

    project["path"] = project_path
    project["project"] = formatters.get_project_id_from_project_path(project_path)

    roles = project_roles(ctx, project_path, formatters.format_string_to_boolean(show_service_accounts))
    project["contributors"] = roles["modify_object"]
    project["managers"] = roles["own"]
    project["viewers"] = roles["read_object"]
    metadata = collection_metadata(ctx, f"COLL_NAME = {query_value(project_path)}")

    # Get project metadata
    project[ProjectAVUs.TITLE.value] = avu(ctx, metadata, project_path, ProjectAVUs.TITLE.value, "", fatal=True)

    project[ProjectAVUs.ENABLE_ARCHIVE.value] = avu(ctx, metadata, project_path, ProjectAVUs.ENABLE_ARCHIVE.value, FALSE_AS_STRING, fatal=False)

    project[ProjectAVUs.ENABLE_UNARCHIVE.value] = avu(ctx, metadata, project_path, ProjectAVUs.ENABLE_UNARCHIVE.value, project[ProjectAVUs.ENABLE_ARCHIVE.value], fatal=False)

    project[ProjectAVUs.ENABLE_CONTRIBUTOR_EDIT_METADATA.value] = avu(ctx, metadata, project_path, ProjectAVUs.ENABLE_CONTRIBUTOR_EDIT_METADATA.value, FALSE_AS_STRING, fatal=False)

    project[ProjectAVUs.DESCRIPTION.value] = avu(ctx, metadata, project_path, ProjectAVUs.DESCRIPTION.value, "", fatal=False)

    project["respCostCenter"] = avu(ctx, metadata, project_path, ProjectAVUs.RESPONSIBLE_COST_CENTER.value, "", fatal=True)

    project["storageQuotaGiB"] = avu(ctx, metadata, project_path, ProjectAVUs.STORAGE_QUOTA_GB.value, "", fatal=True)

    project[ProjectAVUs.COLLECTION_METADATA_SCHEMAS.value] = avu(ctx, metadata, project_path, ProjectAVUs.COLLECTION_METADATA_SCHEMAS.value, "", fatal=True)

    project[ProjectAVUs.ENABLE_DROPZONE_SHARING.value] = avu(ctx, metadata, project_path, ProjectAVUs.ENABLE_DROPZONE_SHARING.value, FALSE_AS_STRING, fatal=False)

    ret = avu(ctx, metadata, project_path, ProjectAVUs.PRINCIPAL_INVESTIGATOR.value, "", fatal=True)
    if ret == username:
        has_financial_view_access = True
    # Get the display name value for the PI
    for user in project["managers"]["userObjects"]:
        if user["userName"] == ret:
            project["principalInvestigatorDisplayName"] = user["displayName"]

    ret = avu(ctx, metadata, project_path, ProjectAVUs.DATA_STEWARD.value, "", fatal=True)
    if ret == username:
        has_financial_view_access = True
    # Get the display name value for the data steward
    for user in project["managers"]["userObjects"]:
        if user["userName"] == ret:
            project["dataStewardDisplayName"] = user["displayName"]

    project["has_financial_view_access"] = has_financial_view_access

    # Calculate the project's size
    ret = ctx.callback.get_project_size(project["path"], "")["arguments"][1]
    project["dataSizeGiB"] = json.loads(ret)

    return project
