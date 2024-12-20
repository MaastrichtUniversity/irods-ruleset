# Entire collection:
# /rules/tests/run_test.sh -r perform_archive_checks -a "/nlmumc/projects/P000000017/C000000001,dlinssen" -j -u service-surfarchive
import irods_types  # pylint: disable=import-error

from dhpythonirodsutils import formatters, exceptions
from dhpythonirodsutils.enums import ProjectAVUs, ProcessAttribute

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def perform_archive_checks(ctx, archival_path):
    """
    Prepare and execute the tape archival of a single file or complete project collection

        - Check if the path provided is valid (is a project_collection path)
        - Check if the tape and project resource are available
        - Check if the project and collection exist
        - Check if archiving is enabled for this project
        - Check if the caller of the rule is 'service-surfarchive' (the SURF service account)
        - Check if the (un)archive statuses are valid (ie, no other archival related processes are running)

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    archival_path: str
        The full path of the collection to be archived, e.g. '/nlmumc/projects/P000000017/C000000001'
    """
    try:
        project_id = formatters.get_project_id_from_project_collection_path(archival_path)
        project_collection_id = formatters.get_collection_id_from_project_collection_path(archival_path)
        project_collection_path = formatters.format_project_collection_path(project_id, project_collection_id)
        project_path = formatters.format_project_path(project_id)
    except exceptions.ValidationError:
        error_message = "Invalid path to archive: '{}'".format(archival_path)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
        ctx.callback.msiObjStat(project_collection_path, irods_types.RodsObjStat())
    except RuntimeError:
        error_message = "Project or project_collection does not exist".format(project_path)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    archive_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_ARCHIVE.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    if not formatters.format_string_to_boolean(archive_enabled):
        error_message = "Archiving is disabled for this project: '{}'".format(project_path)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    tape_resource = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ARCHIVE_DESTINATION_RESOURCE.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]

    project_resource = ctx.callback.getCollectionAVU(project_path, ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING)[
        "arguments"
    ][2]

    tape_resource_status = ctx.callback.get_resource_status(tape_resource, "")["arguments"][1]
    project_resource_status = ctx.callback.get_resource_status(project_resource, "")["arguments"][1]
    if tape_resource_status == "down" or project_resource_status == "down":
        error_message = "The project or tape resource is currently unavailable: archiving is not possible"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    service_account = ctx.callback.getResourceAVU(tape_resource, "service-account", "", "0", "false")["arguments"][2]

    # The minimum file size criteria (in bytes)
    minimum_file_size = ctx.callback.getResourceAVU(tape_resource, "minimumFileSize", "", "0", "false")["arguments"][2]

    current_user = ctx.callback.get_client_username("")["arguments"][0]
    if current_user != service_account:
        error_message = "Archiving is only possible when being called by '{}'".format(service_account)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    archive_state = ctx.callback.getCollectionAVU(
        project_collection_path, ProcessAttribute.ARCHIVE.value, "", "", FALSE_AS_STRING
    )["arguments"][2]
    unarchive_state = ctx.callback.getCollectionAVU(
        project_collection_path, ProcessAttribute.UNARCHIVE.value, "", "", FALSE_AS_STRING
    )["arguments"][2]

    if archive_state != "" or unarchive_state != "":
        error_message = "Not permitted to start archival in state 'archive_state:{}' 'unarchive_state:{}".format(
            archive_state, unarchive_state
        )
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    return {
        "service_account": service_account,
        "project_collection_path": project_collection_path,
        "project_id": project_id,
        "project_collection_id": project_collection_id,
        "tape_resource": tape_resource,
        "minimum_file_size": minimum_file_size,
    }
