# Part of the archival flow. Not to be called by user
import irods_types  # pylint: disable=import-error
import json

from dhpythonirodsutils.enums import ProjectAVUs, ProcessAttribute

from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING, irepl_wrapper


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def perform_unarchive(ctx, check_results, username_initiator):
    """
    Handle the unarchival flow and clean up afterwards.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    archival_path: str
        The full path of the collection OR file to be unarchived, e.g. '/nlmumc/projects/P000000017/C000000001'  '/nlmumc/projects/P000000017/C000000001/300M.bin'
    check_results: dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    """
    check_results = json.loads(check_results)
    files_to_unarchive = get_files_to_unarchive(ctx, check_results)
    files_unarchived = 0
    if files_to_unarchive:
        project_resource = ctx.callback.getCollectionAVU(
            format_project_path(ctx, check_results["project_id"]), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        files_unarchived = unarchive_files(ctx, files_to_unarchive, check_results, project_resource, username_initiator)
    
    clean_up_and_inform(ctx, check_results, files_unarchived)


def unarchive_files(ctx, files_to_unarchive, check_results, project_resource, username_initiator):
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
    files_to_unarchive: dict
        The files to archive
    check_results: dict
        The dict containing all the information gained by the 'perform_unarchive_checks' rule.
    username_initiator: str
        The user that initiated this entire flow. Used when creating a JIRA ticket on error.
    """
    files_unarchived = 0
    for file in files_to_unarchive:
        set_tape_avu(
            ctx,
            check_results["project_collection_path"],
            "unarchive-in-progress {}/{}".format(files_unarchived + 1, len(files_to_unarchive)),
        )

        # Checksum
        checksum = ctx.callback.msiDataObjChksum(file["virtual_path"], "", "")["arguments"][2]
        ctx.callback.msiWriteRodsLog("DEBUG: chksum done {}".format(checksum), 0)

        # Replicate
        try:
            irepl_wrapper(ctx, file["virtual_path"], project_resource, check_results["service_account"], False, False)
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.UNARCHIVE.value,
                "error-unarchive-failed",
                "Replication of {} from {} to {} FAILED.".format(
                    file["virtual_path"], check_results["archive_destination_resource"], project_resource
                ),
            )

        # Trim
        try:
            ctx.callback.msiDataObjTrim(
                file["virtual_path"], check_results["archive_destination_resource"], "null", "2", "null", 0
            )
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.UNARCHIVE.value,
                "error-unarchive-failed",
                "Trim of {} from {} FAILED.".format(
                    file["virtual_path"], check_results["archive_destination_resource"]
                ),
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
    set_tape_avu(ctx, check_results["project_collection_path"], "unarchive-done")
    ctx.callback.msiWriteRodsLog("DEBUG: surfArchiveScanner unarchived {} files".format(files_unarchived), 0)

    kvp = ctx.callback.msiString2KeyValPair(
        "{}={}".format(ProcessAttribute.UNARCHIVE.value, "unarchive-done"), irods_types.BytesBuf()
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
    """
    dm_attr_output = json.loads(
        ctx.callback.dm_attr(
            check_results["unarchival_path"],
            check_results["archive_destination_resource"],
            check_results["resource_location"],
            "",
        )["arguments"][3]
    )
    return dm_attr_output["files_online"]
