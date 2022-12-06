# /rules/tests/run_test.sh -r validate_dropzone -a "/nlmumc/ingest/direct/concerned-opossum,jmelius,direct" -j -u jmelius
import irods_types  # pylint: disable=import-error

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs, DropzoneState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def validate_dropzone(ctx, dropzone_path, username, dropzone_type):
    """
    Validate if the dropzone and depositor are eligible for ingestion by:
        - Check if user has dropzone permissions
        - Check if depositor is the creator of the dropzone (only in direct ingest)
        - Check if the dropzone exists
        - Check if the linked project ID exists
        - Check if the state is OK
        - Validate the metadata
        - Get necessary AVU's and return them

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path: str
        The full dropzone path, e.g. '/nlmumc/ingest/direct/crazy-frog' or '/nlmumc/ingest/zones/crazy-frog'
    username: str
        The username of the depositor, e.g. dlinssen
    dropzone_type: str
        The type of dropzone, e.g. direct or mounted
    """
    # Check if ingesting user has dropzone permissions
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, dropzone_type, "")["arguments"][2]
    if not formatters.format_string_to_boolean(has_dropzone_permission):
        ctx.callback.msiExit(
            "-818000", "User '{}' has insufficient DropZone permissions on '{}'".format(username, dropzone_path)
        )

    # Check if dropzone exists
    try:
        ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    # Get dropzone metadata
    project_id = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    project_path = format_project_path(ctx, project_id)

    # Check if project path exists
    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown project: {}".format(project_id))

    sharing_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_DROPZONE_SHARING.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)

    # If direct ingest: check if user ingesting is the creator or Dropzone sharing is enabled.
    if dropzone_type == "direct" and username != "rods" and not sharing_enabled:
        creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
        if creator != username:
            ctx.callback.msiExit(
                "-818000", "User '{}' is not the creator of dropzone '{}'".format(username, dropzone_path)
            )

    title = ctx.callback.getCollectionAVU(dropzone_path, "title", "", "", TRUE_AS_STRING)["arguments"][2]
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]

    # Get resource availability -- check ingest & destination resource
    available = ctx.callback.get_project_resource_availability(
        project_id, TRUE_AS_STRING, TRUE_AS_STRING, FALSE_AS_STRING, ""
    )["arguments"][4]

    # Project or ingest resource is not available, abort ingest
    if not formatters.format_string_to_boolean(available):
        # -831000 CAT_INVALID_RESOURCE
        ctx.callback.msiExit(
            "-831000", "The project or ingest resource is disabled for this project '{}'".format(project_id)
        )

    # Check for valid state to start ingestion
    ingestable = ctx.callback.is_dropzone_state_ingestable(state, "")["arguments"][1]
    if not formatters.format_string_to_boolean(ingestable):
        ctx.callback.msiExit("-1", "Invalid state to start ingestion.")

    ctx.callback.msiWriteRodsLog("Starting validation of {}:".format(dropzone_path), 0)
    # Set 'state' AVU to 'validating'
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.VALIDATING.value)

    validation_result = ctx.callback.validate_metadata(dropzone_path, "")["arguments"][1]
    return {"project_id": project_id, "title": title, "validation_result": validation_result}
