# DONOTCALLDIRECTLY
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
    # Initialize validation error list
    validation_errors = []

    # Check if ingesting user has dropzone permissions
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, dropzone_type, "")["arguments"][2]
    if not formatters.format_string_to_boolean(has_dropzone_permission):
        validation_errors.append(
            "User '{}' has insufficient DropZone permissions on '{}'".format(username, dropzone_path)
        )

    # Check if dropzone exists
    validation_errors = check_if_dropzone_exists(ctx, dropzone_path, validation_errors)

    # Get dropzone metadata
    project_id = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    project_path = format_project_path(ctx, project_id)

    # Check if project path exists
    validation_errors = check_if_project_exists(ctx, project_path, project_id, validation_errors)

    # Check if user is allowed to start this specific ingest
    validation_errors = check_if_user_is_allowed_to_start_ingest(
        ctx, project_path, dropzone_type, username, dropzone_path, validation_errors
    )

    # Get resource availability -- check ingest & destination resource
    available = ctx.callback.get_project_resource_availability(
        project_id, TRUE_AS_STRING, TRUE_AS_STRING, FALSE_AS_STRING, ""
    )["arguments"][4]

    # Project or ingest resource is not available, abort ingest
    if not formatters.format_string_to_boolean(available):
        validation_errors.append("The project or ingest resource is disabled for this project '{}'".format(project_id))

    ctx.callback.msiWriteRodsLog("Starting validation of {}:".format(dropzone_path), 0)

    # Set 'state' AVU to 'validating'
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.VALIDATING.value)

    # Start metadata validation
    validation_result = ctx.callback.validate_metadata(dropzone_path, "")["arguments"][1] == TRUE_AS_STRING
    if not validation_result:
        validation_errors.append("Metadata validation failed")

    # Create a document with the dropzone info at this stage of the ingest procedure
    validation_errors = create_pre_ingest_document(
        ctx, dropzone_type, project_id, dropzone_path, username, validation_errors
    )

    # Check if the dropzone is valid for ingestion
    # see bug https://github.com/irods/irods/issues/7302
    validation_errors = is_dropzone_ingestable(ctx, dropzone_path, validation_errors)

    return {"project_id": project_id, "validation_errors": validation_errors}


def is_dropzone_ingestable(ctx, dropzone_path, validation_errors):
    is_ingestable = ctx.callback.getCollectionAVU(dropzone_path, "isIngestable", "", "", TRUE_AS_STRING)["arguments"][2]
    if not formatters.format_string_to_boolean(is_ingestable):
        validation_errors.append("Dropzone contains unsupported characters in filenames and/or directories")
    return validation_errors


def check_if_dropzone_exists(ctx, dropzone_path, validation_errors):
    try:
        ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    except RuntimeError:
        validation_errors.append("Dropzone '{}' does not exist".format(dropzone_path))
    return validation_errors


def check_if_project_exists(ctx, project_path, project_id, validation_errors):
    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
    except RuntimeError:
        validation_errors.append("Unknown project: {}".format(project_id))
    return validation_errors


def create_pre_ingest_document(ctx, dropzone_type, project_id, dropzone_path, username, validation_errors):
    ingest_resource_host = ctx.callback.get_dropzone_resource_host(dropzone_type, project_id, "")["arguments"][2]
    try:
        ctx.remoteExec(
            ingest_resource_host,
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            "save_dropzone_pre_ingest_info('{}', '{}', '{}')".format(dropzone_path, username, dropzone_type),
            "",
        )
    except RuntimeError:
        validation_errors.append("Failed creating dropzone pre-ingest information")
    ctx.callback.msiWriteRodsLog(
        "DEBUG: dropzone pre-ingest information created on {} for {}".format(ingest_resource_host, dropzone_path), 0
    )
    return validation_errors


def check_if_user_is_allowed_to_start_ingest(
    ctx, project_path, dropzone_type, username, dropzone_path, validation_errors
):
    sharing_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_DROPZONE_SHARING.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)

    # If direct ingest: check if user ingesting is the creator or Dropzone sharing is enabled.
    if dropzone_type == "direct" and username != "rods" and not sharing_enabled:
        creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
        if creator != username:
            validation_errors.append("User '{}' is not the creator of dropzone '{}'".format(username, dropzone_path))
    return validation_errors
