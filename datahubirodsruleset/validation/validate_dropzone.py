# DONOTCALLDIRECTLY
import irods_types  # pylint: disable=import-error

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs, DropzoneState
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

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
            f"User '{username}' has insufficient DropZone permissions on '{dropzone_path}'"
        )

    # Check if dropzone exists
    validation_errors = check_if_dropzone_exists(ctx, dropzone_path, validation_errors)
    # If validation errors at this point, return immediately since the rest of the validation relies on the dropzone existing
    if validation_errors:
        return {"project_id": "dz-does-not-exist", "validation_errors": validation_errors}
    
    ctx.callback.msiWriteRodsLog(f"Starting validation of {dropzone_path}:", 0)

    # Set 'state' AVU to 'validating'
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.VALIDATING.value)

    # Get dropzone metadata
    project_id = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    project_path = format_project_path(ctx, project_id)

    # Check if project path exists
    validation_errors = check_if_project_exists(ctx, project_path, project_id, validation_errors)
    # If validation errors at this point, return immediately since the rest of the validation relies on the project existing
    if validation_errors:
        return {"project_id": project_id, "validation_errors": validation_errors}

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
        validation_errors.append(f"The project or ingest resource is disabled for this project '{project_id}'")

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
    if dropzone_type == "direct":
        validation_errors = does_dropzone_contain_stale_or_locked_files(ctx, dropzone_path, validation_errors)

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
        validation_errors.append(f"Dropzone '{dropzone_path}' does not exist")
    return validation_errors


def check_if_project_exists(ctx, project_path, project_id, validation_errors):
    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
    except RuntimeError:
        validation_errors.append(f"Unknown project: {project_id}")
    return validation_errors


def create_pre_ingest_document(ctx, dropzone_type, project_id, dropzone_path, username, validation_errors):
    ingest_resource_host = ctx.callback.get_dropzone_resource_host(dropzone_type, project_id, "")["arguments"][2]
    try:
        ctx.remoteExec(
            ingest_resource_host,
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            f"save_dropzone_pre_ingest_info('{dropzone_path}', '{username}', '{dropzone_type}')",
            "",
        )
    except RuntimeError:
        validation_errors.append("Failed creating dropzone pre-ingest information")
    ctx.callback.msiWriteRodsLog(
        f"DEBUG: dropzone pre-ingest information created on {ingest_resource_host} for {dropzone_path}", 0
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
            validation_errors.append(f"User '{username}' is not the creator of dropzone '{dropzone_path}'")
    return validation_errors

def does_dropzone_contain_stale_or_locked_files(ctx, dropzone_path, validation_errors):
    for failed_data_object in row_iterator(
        "COLL_NAME,DATA_NAME,DATA_REPL_NUM,DATA_REPL_STATUS",
        f"COLL_NAME LIKE '{dropzone_path}%' AND DATA_REPL_STATUS != '1'",
        AS_LIST,
        ctx.callback
    ):
        data_path = f"{failed_data_object[0]}/{failed_data_object[1]}"
        if failed_data_object[3] == "0":
            validation_errors.append(f"Dropzone contains stale file '{data_path}'")
        elif failed_data_object[3] in ("2", "3", "4"):
            validation_errors.append(f"Dropzone contains locked file '{data_path}'")
        else:
            validation_errors.append(f"Dropzone contains file with unknown replication status '{data_path}'")
    return validation_errors
