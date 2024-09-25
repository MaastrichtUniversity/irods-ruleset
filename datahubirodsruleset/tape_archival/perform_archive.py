# Part of the archival flow. Not to be called by user
import irods_types  # pylint: disable=import-error
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error
import json

from dhpythonirodsutils.enums import ProcessAttribute, ArchiveState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, irepl_wrapper


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
        checksum = ctx.callback.msiDataObjChksum(file["path"], "", "")["arguments"][2]
        ctx.callback.msiWriteRodsLog("DEBUG: chksum done {}".format(checksum), 0)

        # Replicate
        try:
            irepl_wrapper(
                ctx, file["path"], check_results["tape_resource"], check_results["service_account"], False, False
            )
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.ARCHIVE.value,
                ArchiveState.ERROR_ARCHIVE_FAILED.value,
                "Replication of {} from {} to {} FAILED.".format(
                    file["path"], file["coordinating_resource"], check_results["tape_resource"]
                ),
            )

        # Trim
        try:
            ctx.callback.msiDataObjTrim(file["path"], file["coordinating_resource"], "null", "1", "null", 0)
        except RuntimeError as err:
            ctx.callback.msiWriteRodsLog(err, 0)
            ctx.callback.set_tape_error_avu(
                check_results["project_collection_path"],
                username_initiator,
                ProcessAttribute.ARCHIVE.value,
                ArchiveState.ERROR_ARCHIVE_FAILED.value,
                "Trim of {} from {} FAILED.".format(file["path"], file["coordinating_resource"]),
            )

        files_archived += 1
    return files_archived


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
            "RESC_NAME, RESC_ID", "RESC_ID = '{}'".format(resc[0]), AS_LIST, ctx.callback
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
    files_unarchived: int
        The amount of files archived by this rule
    """
    set_tape_avu(ctx, check_results["project_collection_path"], ArchiveState.ARCHIVE_DONE.value)
    ctx.callback.msiWriteRodsLog("DEBUG: surfArchiveScanner archived {} files".format(files_archived), 0)

    kvp = ctx.callback.msiString2KeyValPair(
        "{}={}".format(ProcessAttribute.ARCHIVE.value, ArchiveState.ARCHIVE_DONE.value), irods_types.BytesBuf()
    )["arguments"][1]
    ctx.callback.msiRemoveKeyValuePairsFromObj(kvp, check_results["project_collection_path"], "-C")

    if files_archived:
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
        "COLL_NAME LIKE '{}%' AND DATA_RESC_NAME != '{}' AND DATA_SIZE >= '{}'".format(
            archival_path, check_results["tape_resource"], check_results["minimum_file_size"]
        ),
        AS_LIST,
        ctx.callback,
    ):
        files_to_archive.append(
            {
                "path": "{}/{}".format(row[1], row[2]),
                "parent_resource_id": row[0],
                "coordinating_resource": coordinating_resources[row[0]],
            }
        )
    return files_to_archive
