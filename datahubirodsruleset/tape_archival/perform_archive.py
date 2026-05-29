# Part of the archival flow. Not to be called by user
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error
import json

from dhpythonirodsutils.enums import ProcessAttribute, ArchiveState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, irepl_wrapper
from datahubirodsruleset.tape_archival.tape_utils import checksum_file, finalize_tape_operation, retry_runtime_error


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def perform_archive(ctx, archival_path, check_results, username_initiator):
    """
    Handle the archival flow and clean up afterwards.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    archival_path: str
        The full path of the collection to be archived, e.g. '/nlmumc/projects/P000000017/C000000001'
    check_results: dict
        The dict containing all the information gained by the 'perform_archive_checks' rule.
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    """
    coordinating_resources = get_coordinating_resources(ctx)
    check_results = json.loads(check_results)
    files_to_archive = get_files_to_archive(ctx, archival_path, check_results, coordinating_resources)

    if files_to_archive:
        value = ArchiveState.NUMBER_OF_FILES_FOUND.value.format(len(files_to_archive))
        ctx.callback.msiWriteRodsLog(
            f"INFO: Archival workflow started for {archival_path} ({len(files_to_archive)!s} file(s))",
            0,
        )
        set_tape_avu(ctx, check_results["project_collection_path"], value)
        files_archived = archive_files(ctx, files_to_archive, check_results, username_initiator)
        clean_up_and_inform(ctx, check_results, files_archived)
    else:
        ctx.callback.msiWriteRodsLog("INFO: Nothing to archive, no files match criteria", 0)
        clean_up_and_inform(ctx, check_results, 0)


def archive_files(ctx, files_to_archive, check_results, username_initiator):
    """
    Actually archive the files.
    For all files passed, this does the following:
    - Checksum
    - Replicate to tape
    - Trim the coordinating resource off

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    files_to_archive: list
        The files to archive
    check_results: dict
        The dict containing all the information gained by the 'perform_archive_checks' rule.
    username_initiator: str
        The user that initiated this entire flow. Used when creating a JIRA ticket on error.

    Returns
    ----------
    str
        The count of total files archived by this process
    """
    files_archived = 0
    for file in files_to_archive:
        set_tape_avu(
            ctx,
            check_results["project_collection_path"],
            ArchiveState.ARCHIVE_IN_PROGESS.value.format(files_archived + 1, len(files_to_archive)),
        )

        # Checksum
        # We perform checksums beforehand because the 'irepl' command does not include checksumming
        if not _run_archive_step(
            ctx,
            check_results,
            username_initiator,
            f"Checksum {file['path']}",
            f"Checksum of {file['path']} from {file['coordinating_resource']} FAILED.",
            lambda: checksum_file(ctx, file["path"]),
        ):
            continue

        # Replicate
        if not _run_archive_step(
            ctx,
            check_results,
            username_initiator,
            f"Replication {file['path']} to {check_results['tape_resource']}",
            f"Replication of {file['path']} from {file['coordinating_resource']} to {check_results['tape_resource']} FAILED.",
            lambda: irepl_wrapper(
                ctx,
                file["path"],
                check_results["tape_resource"],
                check_results["service_account"],
                False,
                True,
            ),
        ):
            continue

        # Trim
        if not _run_archive_step(
            ctx,
            check_results,
            username_initiator,
            f"Trim {file['path']} from {file['coordinating_resource']}",
            f"Trim of {file['path']} from {file['coordinating_resource']} FAILED.",
            lambda: ctx.callback.msiDataObjTrim(file["path"], file["coordinating_resource"], "null", "1", "null", 0),
        ):
            continue

        files_archived += 1
    return files_archived


def _run_archive_step(ctx, check_results, username_initiator, operation_name, failure_message, operation):
    """
    Run a single archive step with retries, setting the error AVU on failure.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results : dict
        The dict containing all the information gained by the 'perform_archive_checks' rule.
    username_initiator : str
        The user that initiated this entire flow.
    operation_name : str
        Human-readable descriptor for log messages, e.g. 'Checksum /path/to/file'
    failure_message : str
        Message to pass to set_tape_error_avu on failure.
    operation : Callable
        The operation to attempt.

    Returns
    -------
    bool
        True on success, False if all retries failed.
    """
    success = retry_runtime_error(ctx, operation_name, operation)
    if not success:
        ctx.callback.set_tape_error_avu(
            check_results["project_collection_path"],
            username_initiator,
            ProcessAttribute.ARCHIVE.value,
            ArchiveState.ERROR_ARCHIVE_FAILED.value,
            failure_message,
        )
    return success


def get_coordinating_resources(ctx):
    """
    Query all coordinating resources. This is to avoid just assuming a file is on the resource that it SHOULD be on.
    So we can trim the file after moving to tape, even if the file is not on the resource that is should be on.

    Example:
    Project resource = replRescUMCeph01
    Single file in project collection is on stagingResc01 due to some quirk during ingest
    When moving project collection to tape, this file is still trimmed off (due to the trim knowing to trim stagingResc01)

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    ----------
    dict
        A dictionary containing coordinating resources and their iRODS IDs
    """
    resources = {}
    for resc in row_iterator(
        "RESC_PARENT,RESC_LOC", "RESC_LOC != 'EMPTY_RESC_HOST' AND RESC_PARENT != ''", AS_LIST, ctx.callback
    ):
        for resource_information in row_iterator(
            "RESC_NAME, RESC_ID", f"RESC_ID = '{resc[0]}'", AS_LIST, ctx.callback
        ):
            resources[resource_information[1]] = resource_information[0]
    return resources


def clean_up_and_inform(ctx, check_results, files_archived):
    """
    Handle the end of the rule, clean up the AVU, inform the DevOps (elastalert),
    close the PC, re-calculate the collection size for billing

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results: dict
        The dict containing all the information gained by the 'perform_archive_checks' rule.
    files_archived: int
        The amount of files archived by this rule
    """
    finalize_tape_operation(
        ctx,
        check_results,
        files_archived,
        ArchiveState.ARCHIVE_DONE.value,
        ProcessAttribute.ARCHIVE.value,
        "archived",
    )


def set_tape_avu(ctx, project_collection_path, value):
    """
    A simple wrapper around setCollectionAVU to not have that code duplicated across the rule

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path: str
        The PC to set the archive AVU on
    value: str
        The value to set
    """
    ctx.callback.setCollectionAVU(project_collection_path, ProcessAttribute.ARCHIVE.value, value)


def get_files_to_archive(ctx, archival_path, check_results, coordinating_resources):
    """
    Query what files we need to archive

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    archival_path: str
        The path provided by the user to archive
    check_results: dict
        The dict containing all the information gained by the 'perform_archive_checks' rule.
    coordinating_resources: dict
        A dictionary of coordinating resources with their ID and name

    Returns
    ----------
    dict
        A dictionary containing the path, resource ID and current coordinating resource of the data object to be archived
    """
    files_to_archive = []

    for row in row_iterator(
        "RESC_PARENT,COLL_NAME,DATA_NAME",
        f"COLL_NAME LIKE '{archival_path}%' AND DATA_RESC_NAME != '{check_results['tape_resource']}' AND DATA_SIZE >= '{check_results['minimum_file_size']}'",
        AS_LIST,
        ctx.callback,
    ):
        files_to_archive.append(
            {
                "path": f"{row[1]}/{row[2]}",
                "parent_resource_id": row[0],
                "coordinating_resource": coordinating_resources[row[0]],
            }
        )
    return files_to_archive
