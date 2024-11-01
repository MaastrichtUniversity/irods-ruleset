# Entire collection:
# /rules/tests/run_test.sh -r perform_unarchive_checks -a "/nlmumc/projects/P000000017/C000000001,dlinssen" -j -u service-surfarchive
# Single file:
# /rules/tests/run_test.sh -r perform_unarchive_checks -a "/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log,dlinssen" -j -u service-surfarchive
import irods_types  # pylint: disable=import-error
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from dhpythonirodsutils import formatters, exceptions
from dhpythonirodsutils.enums import ProjectAVUs, ProcessAttribute

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def perform_unarchive_checks(ctx, unarchival_path):
    """
    Prepare and execute the tape unarchival of a single file or complete project collection

        - Check if the path provided is valid (is a project_collection path or file in a project_collection path)
        - Check if the project and collection exist
        - Check if the tape and project resource are available
        - Check if unarchiving is enabled for this project
        - Check if the caller of the rule is 'service-surfarchive' (the SURF service account)
        - Check if the (un)archive states are valid (ie, no other archival related processes are running)

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    unarchival_path: str
        The full path of the collection OR file to be unarchived, e.g. '/nlmumc/projects/P000000017/C000000001' or '/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log'

    Returns
    ----------
    dict
        A dictionary containing information obtained with verification and needed in the unarchival process
    """
    try:
        project_id = formatters.get_project_id_from_project_collection_path(unarchival_path)
        project_collection_id = formatters.get_collection_id_from_project_collection_path(unarchival_path)
        project_collection_path = formatters.format_project_collection_path(project_id, project_collection_id)
        project_path = formatters.format_project_path(project_id)
    except exceptions.ValidationError:
        error_message = "Invalid path to unarchive: '{}'".format(unarchival_path)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    try:
        ctx.callback.msiObjStat(project_path, irods_types.RodsObjStat())
        ctx.callback.msiObjStat(project_collection_path, irods_types.RodsObjStat())
    except RuntimeError:
        error_message = "Project or project_collection does not exist".format(project_path)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    unarchive_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_UNARCHIVE.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    if not formatters.format_string_to_boolean(unarchive_enabled):
        error_message = "Unarchiving is disabled for this project: '{}'".format(project_path)
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
        error_message = "The project or tape resource is currently unavailable: unarchiving is not possible"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    service_account = ctx.callback.getResourceAVU(tape_resource, "service-account", "", "0", "false")["arguments"][2]

    current_user = ctx.callback.get_client_username("")["arguments"][0]
    if current_user != service_account:
        error_message = "Unarchiving is only possible when being called by '{}'".format(service_account)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    archive_state = ctx.callback.getCollectionAVU(
        project_collection_path, ProcessAttribute.ARCHIVE.value, "", "", FALSE_AS_STRING
    )["arguments"][2]
    unarchive_state = ctx.callback.getCollectionAVU(
        project_collection_path, ProcessAttribute.UNARCHIVE.value, "", "", FALSE_AS_STRING
    )["arguments"][2]

    if archive_state != "" or unarchive_state != "":
        error_message = "Not permitted to start unarchival in state 'archive_state:{}' 'unarchive_state:{}".format(
            archive_state, unarchive_state
        )
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(tape_resource), AS_LIST, ctx.callback):
        tape_resource_location = row[0]

    return {
        "service_account": service_account,
        "project_collection_path": project_collection_path,
        "project_id": project_id,
        "project_collection_id": project_collection_id,
        "tape_resource_location": tape_resource_location,
        "tape_resource": tape_resource,
        "project_resource": project_resource,
    }
