# Part of the unarchival flow. Not to be called by user
import irods_types  # pylint: disable=import-error
import json

from dhpythonirodsutils.enums import ProcessAttribute, UnarchiveState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, irepl_wrapper
from datahubirodsruleset.tape_archival.dm_attr import dm_attr


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
            "INFO: UnArchival workflow started for {} ({} file(s))".format(
                check_results["unarchival_path"], str(len(files_to_unarchive))
            ),
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
        try:
            checksum = ctx.callback.msiDataObjChksum(file["virtual_path"], "", "")["arguments"][2]
            ctx.callback.msiWriteRodsLog("DEBUG: chksum done {}".format(checksum), 0)
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.UNARCHIVE.value,
                UnarchiveState.ERROR_UNARCHIVE_FAILED.value,
                "Checksum of {} from {} FAILED.".format(file["virtual_path"], check_results["tape_resource"]),
            )

        # Replicate
        try:
            irepl_wrapper(
                ctx,
                file["virtual_path"],
                check_results["project_resource"],
                check_results["service_account"],
                False,
                True
            )
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.UNARCHIVE.value,
                UnarchiveState.ERROR_UNARCHIVE_FAILED.value,
                "Replication of {} from {} to {} FAILED.".format(
                    file["virtual_path"], check_results["tape_resource"], check_results["project_resource"]
                ),
            )

        # Trim
        try:
            ctx.callback.msiDataObjTrim(file["virtual_path"], check_results["tape_resource"], "null", "2", "null", 0)
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.UNARCHIVE.value,
                UnarchiveState.ERROR_UNARCHIVE_FAILED.value,
                "Trim of {} from {} FAILED.".format(file["virtual_path"], check_results["tape_resource"]),
            )

        files_unarchived += 1

    return files_unarchived


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
    set_tape_avu(ctx, check_results["project_collection_path"], UnarchiveState.UNARCHIVE_DONE.value)
    ctx.callback.msiWriteRodsLog("DEBUG: surfArchiveScanner unarchived {} files".format(files_unarchived), 0)

    kvp = ctx.callback.msiString2KeyValPair(
        "{}={}".format(ProcessAttribute.UNARCHIVE.value, UnarchiveState.UNARCHIVE_DONE.value), irods_types.BytesBuf()
    )["arguments"][1]
    ctx.callback.msiRemoveKeyValuePairsFromObj(kvp, check_results["project_collection_path"], "-C")

    if files_unarchived:
        ctx.callback.setCollectionSize(
            check_results["project_id"], check_results["project_collection_id"], FALSE_AS_STRING, FALSE_AS_STRING
        )
        ctx.callback.msiWriteRodsLog("DEBUG: dcat:byteSize and numFiles have been re-calculated and adjusted", 0)
    ctx.callback.close_project_collection(check_results["project_id"], check_results["project_collection_id"])


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
