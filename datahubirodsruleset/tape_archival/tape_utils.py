"""Shared helpers for the tape archive and unarchive flows."""
import irods_types  # pylint: disable=import-error
import time

from dhpythonirodsutils import formatters, exceptions
from dhpythonirodsutils.enums import ProjectAVUs, ProcessAttribute

from datahubirodsruleset.utils import FALSE_AS_STRING, TRUE_AS_STRING


MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 60


# ---------------------------------------------------------------------------
# Helpers shared by perform_archive_checks and perform_unarchive_checks
# ---------------------------------------------------------------------------


def parse_project_collection_path(ctx, path, operation):
    """
    Parse and validate a project collection path, exiting on invalid input.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    path : str
        The path to parse, e.g. '/nlmumc/projects/P000000017/C000000001'
    operation : str
        Human-readable label used in the error message, e.g. 'archive' or 'unarchive'

    Returns
    -------
    tuple[str, str, str, str]
        (project_id, project_collection_id, project_collection_path, project_path)
    """
    try:
        project_id = formatters.get_project_id_from_project_collection_path(path)
        project_collection_id = formatters.get_collection_id_from_project_collection_path(path)
        project_collection_path = formatters.format_project_collection_path(project_id, project_collection_id)
        project_path = formatters.format_project_path(project_id)
    except exceptions.ValidationError:
        error_message = f"Invalid path to {operation}: '{path}'"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)
    return project_id, project_collection_id, project_collection_path, project_path


def check_project_collection_exists(ctx, project_path, project_collection_path):
    """
    Verify that both the project and project collection exist in iRODS, exiting on failure.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path : str
    project_collection_path : str
    """
    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
        ctx.callback.msiObjStat(project_collection_path, irods_types.RodsObjStat())
    except RuntimeError:
        error_message = "Project or project_collection does not exist"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)


def get_project_resources(ctx, project_path):
    """
    Retrieve the tape and project resource names from the project AVUs.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path : str

    Returns
    -------
    tuple[str, str]
        (tape_resource, project_resource)
    """
    tape_resource = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ARCHIVE_DESTINATION_RESOURCE.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    project_resource = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]
    return tape_resource, project_resource


def check_resources_available(ctx, tape_resource, project_resource, operation):
    """
    Verify that both resources are online, exiting if either is down.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    tape_resource : str
    project_resource : str
    operation : str
        Human-readable label for the error message, e.g. 'archiving' or 'unarchiving'
    """
    tape_resource_status = ctx.callback.get_resource_status(tape_resource, "")["arguments"][1]
    project_resource_status = ctx.callback.get_resource_status(project_resource, "")["arguments"][1]
    if tape_resource_status == "down" or project_resource_status == "down":
        error_message = f"The project or tape resource is currently unavailable: {operation} is not possible"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)


def get_service_account(ctx, tape_resource):
    """
    Retrieve the service account associated with the tape resource.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    tape_resource : str

    Returns
    -------
    str
    """
    return ctx.callback.getResourceAVU(tape_resource, "service-account", "", "0", "false")["arguments"][2]


def validate_caller_is_service_account(ctx, service_account, operation):
    """
    Exit with an error if the calling user is not the service account.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    service_account : str
    operation : str
        Human-readable label for the error message, e.g. 'Archiving' or 'Unarchiving'
    """
    current_user = ctx.callback.get_client_username("")["arguments"][0]
    if current_user != service_account:
        error_message = f"{operation} is only possible when being called by '{service_account}'"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)


def validate_no_active_process(ctx, project_collection_path, operation):
    """
    Exit with an error if an archive or unarchive process is already active.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path : str
    operation : str
        Human-readable label for the error message, e.g. 'archival' or 'unarchival'
    """
    archive_state = ctx.callback.getCollectionAVU(
        project_collection_path, ProcessAttribute.ARCHIVE.value, "", "", FALSE_AS_STRING
    )["arguments"][2]
    unarchive_state = ctx.callback.getCollectionAVU(
        project_collection_path, ProcessAttribute.UNARCHIVE.value, "", "", FALSE_AS_STRING
    )["arguments"][2]
    if archive_state != "" or unarchive_state != "":
        error_message = (
            f"Not permitted to start {operation} in state "
            f"'archive_state:{archive_state}' 'unarchive_state:{unarchive_state}"
        )
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)


# ---------------------------------------------------------------------------
# Helper shared by perform_archive and perform_unarchive
# ---------------------------------------------------------------------------


def finalize_tape_operation(ctx, check_results, files_processed, done_state, process_attribute, verb):
    """
    Clean up the tape AVU and collection after an archive or unarchive operation completes.

    Sets the done-state AVU, removes it from the collection, recalculates the
    collection size when files were processed, then closes the project collection.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results : dict
        The dict containing all the information gained by the checks rule.
    files_processed : int
        Number of files that were actually archived or unarchived.
    done_state : str
        The AVU value that marks the operation as complete,
        e.g. ArchiveState.ARCHIVE_DONE.value
    process_attribute : str
        The AVU attribute name for the operation,
        e.g. ProcessAttribute.ARCHIVE.value
    verb : str
        Past-tense verb used in the log message, e.g. 'archived' or 'unarchived'
    """
    ctx.callback.setCollectionAVU(check_results["project_collection_path"], process_attribute, done_state)
    ctx.callback.msiWriteRodsLog(f"DEBUG: surfArchiveScanner {verb} {files_processed} files", 0)

    kvp = ctx.callback.msiString2KeyValPair(
        f"{process_attribute}={done_state}", irods_types.BytesBuf()
    )["arguments"][1]
    ctx.callback.msiRemoveKeyValuePairsFromObj(kvp, check_results["project_collection_path"], "-C")

    if files_processed:
        ctx.callback.setCollectionSize(
            check_results["project_id"], check_results["project_collection_id"], FALSE_AS_STRING, FALSE_AS_STRING
        )
        ctx.callback.msiWriteRodsLog("DEBUG: dcat:byteSize and numFiles have been re-calculated and adjusted", 0)
    ctx.callback.close_project_collection(check_results["project_id"], check_results["project_collection_id"])


# ---------------------------------------------------------------------------
# Retry infrastructure shared by perform_archive and perform_unarchive
# ---------------------------------------------------------------------------


def retry_runtime_error(ctx, operation_name, operation, retries=MAX_RETRIES, delay_seconds=RETRY_DELAY_SECONDS):
    """
    Retry a callback operation that may transiently fail with RuntimeError.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    operation_name : str
        Human-readable operation descriptor for logs.
    operation : Callable
        The operation to run.
    retries : int
        Total amount of attempts.
    delay_seconds : int
        Delay between attempts.

    Returns
    -------
    bool
        True if operation succeeds, False if all retries fail.
    """
    for attempt in range(1, retries + 1):
        try:
            operation()
            return True
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(str(err), 0)
            if attempt == retries:
                ctx.callback.msiWriteRodsLog(
                    f"ERROR: {operation_name} failed after {retries} attempts",
                    0,
                )
                return False

            ctx.callback.msiWriteRodsLog(
                f"WARNING: {operation_name} failed (attempt {attempt}/{retries}), retrying in {delay_seconds}s",
                0,
            )
            time.sleep(delay_seconds)


def checksum_file(ctx, path):
    """Calculate and verify checksum for a data object path."""
    checksum = ctx.callback.msiDataObjChksum(path, "", "")["arguments"][2]
    ctx.callback.msiWriteRodsLog(f"DEBUG: chksum done {checksum}", 0)
