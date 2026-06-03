# Part of the unarchival flow. Not to be called by user
import json

from dhpythonirodsutils.enums import ProcessAttribute, UnarchiveState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import irepl_wrapper
from datahubirodsruleset.tape_archival.tape_utils import checksum_file, finalize_tape_operation, reset_locked_replicas
from datahubirodsruleset.tape_archival.dm_attr import dm_attr
from datahubirodsruleset.utils import retry_runtime_error

@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def perform_unarchive(ctx, check_results, username_initiator):
    """
    Handle the unarchival flow and clean up afterwards.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results: dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    """
    check_results = json.loads(check_results)
    files_to_unarchive = get_files_to_unarchive(ctx, check_results)
    files_unarchived = 0
    if files_to_unarchive:
        ctx.callback.msiWriteRodsLog(
            f"INFO: UnArchival workflow started for {check_results['unarchival_path']} ({len(files_to_unarchive)!s} file(s))",
            0,
        )
        files_unarchived = unarchive_files(ctx, files_to_unarchive, check_results, username_initiator)

    clean_up_and_inform(ctx, check_results, files_unarchived)


def unarchive_files(ctx, files_to_unarchive, check_results, username_initiator):
    """
    Actually unarchive the files.
    For all files passed, this does the following:
    - Checksum
    - Replicate to project resource
    - Trim the project resource off

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    files_to_unarchive: dict
        The files to unarchive
    check_results: dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.
    username_initiator: str
        The user that initiated this entire flow. Used when creating a JIRA ticket on error.

    Returns
    ----------
    str
        A count of the files unarchived by this process
    """
    files_unarchived = 0
    for file in files_to_unarchive:
        set_tape_avu(
            ctx,
            check_results["project_collection_path"],
            UnarchiveState.UNARCHIVE_IN_PROGESS.value.format(files_unarchived + 1, len(files_to_unarchive)),
        )

        # Checksum
        # We perform checksums beforehand because the 'irepl' command does not include checksumming
        if not _run_unarchive_step(
            ctx,
            check_results,
            username_initiator,
            f"Checksum {file['virtual_path']}",
            f"Checksum of {file['virtual_path']} from {check_results['tape_resource']} FAILED.",
            lambda: checksum_file(ctx, file["virtual_path"]),
        ):
            continue

        # Replicate
        # DHDO-1556 Tape now runs single-threaded since there are network issues preventing multi-threaded running
        # Before each attempt, reset any locked (DATA_REPL_STATUS=2) replica(s) on the project resource left by a
        # previous interrupted run. On unarchive there can be multiple such replicas, so we clear all of them.
        def _do_unarchive_repl():
            reset_locked_replicas(ctx, file["virtual_path"], check_results["project_resource"])
            irepl_wrapper(
                ctx,
                file["virtual_path"],
                check_results["project_resource"],
                check_results["service_account"],
                False,
                True,
            )

        if not _run_unarchive_step(
            ctx,
            check_results,
            username_initiator,
            f"Replication {file['virtual_path']} to {check_results['project_resource']}",
            f"Replication of {file['virtual_path']} from {check_results['tape_resource']} to {check_results['project_resource']} FAILED.",
            _do_unarchive_repl,
        ):
            continue

        # Trim
        if not _run_unarchive_step(
            ctx,
            check_results,
            username_initiator,
            f"Trim {file['virtual_path']} from {check_results['tape_resource']}",
            f"Trim of {file['virtual_path']} from {check_results['tape_resource']} FAILED.",
            lambda: ctx.callback.msiDataObjTrim(
                file["virtual_path"],
                check_results["tape_resource"],
                "null",
                check_results["project_resource_children"],
                "null",
                0,
            ),
        ):
            continue

        files_unarchived += 1

    return files_unarchived


def _run_unarchive_step(ctx, check_results, username_initiator, operation_name, failure_message, operation):
    """
    Run a single unarchive step with retries, setting the error AVU on failure.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results : dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.
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
            ProcessAttribute.UNARCHIVE.value,
            UnarchiveState.ERROR_UNARCHIVE_FAILED.value,
            failure_message,
        )
    return success


def clean_up_and_inform(ctx, check_results, files_unarchived):
    """
    Handle the end of the rule, clean up the AVU, inform the DevOps (elastalert),
    close the PC, re-calculate the collection size for billing

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results: dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.
    files_unarchived: int
        The amount of files unarchived by this rule
    """
    finalize_tape_operation(
        ctx,
        check_results,
        files_unarchived,
        UnarchiveState.UNARCHIVE_DONE.value,
        ProcessAttribute.UNARCHIVE.value,
        "unarchived",
    )


def set_tape_avu(ctx, project_collection_path, value):
    """
    A simple wrapper around setCollectionAVU to not have that code duplicated across the rule

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path: str
        The PC to set the unarchive AVU on
    value: str
        The value to set
    """
    ctx.callback.setCollectionAVU(project_collection_path, ProcessAttribute.UNARCHIVE.value, value)


def get_files_to_unarchive(ctx, check_results):
    """
    We fetch the files to unarchive again here, since iRODS can not properly pass variables
    in between rules. I want to avoid sending a string with 3K files' paths in it with iRODS.
    With fetching the files here again, we keep the big string within this rule.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    check_results: dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.

    Returns
    ----------
    dict
        A dictionary containing the files on tape but online (so ready to unarchive without needing caching)
    """
    dm_attr_output = dm_attr(
        ctx,
        check_results["unarchival_path"],
        check_results["tape_resource"],
        check_results["tape_resource_location"],
    )

    return dm_attr_output["files_online"]
