# Entire collection:
# /rules/tests/run_test.sh -r perform_unarchive_checks -a "/nlmumc/projects/P000000017/C000000001,dlinssen" -j -u service-surfarchive
# Single file:
# /rules/tests/run_test.sh -r perform_unarchive_checks -a "/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log,dlinssen" -j -u service-surfarchive
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING
from datahubirodsruleset.tape_archival.tape_utils import (
    check_project_collection_exists,
    check_resources_available,
    get_project_resources,
    get_service_account,
    parse_project_collection_path,
    validate_caller_is_service_account,
    validate_no_active_process,
)


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
    project_id, project_collection_id, project_collection_path, project_path = parse_project_collection_path(
        ctx, unarchival_path, "unarchive"
    )
    check_project_collection_exists(ctx, project_path, project_collection_path)

    unarchive_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_UNARCHIVE.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    if not formatters.format_string_to_boolean(unarchive_enabled):
        error_message = f"Unarchiving is disabled for this project: '{project_path}'"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    tape_resource, project_resource = get_project_resources(ctx, project_path)
    check_resources_available(ctx, tape_resource, project_resource, "unarchiving")

    service_account = get_service_account(ctx, tape_resource)
    validate_caller_is_service_account(ctx, service_account, "Unarchiving")
    validate_no_active_process(ctx, project_collection_path, "unarchival")

    for row in row_iterator("RESC_LOC", f"RESC_NAME = '{tape_resource}'", AS_LIST, ctx.callback):
        tape_resource_location = row[0]

    # Get the amount of children the project resource has, so we know how many files we should have left after trimming
    for result in row_iterator("RESC_ID", f"RESC_NAME = '{project_resource}'", AS_LIST, ctx.callback):
        resc_id = result[0]
    for result in row_iterator("COUNT(RESC_ID)", f"RESC_PARENT = '{resc_id}'", AS_LIST, ctx.callback):
        total_project_resource_children = result[0]

    return {
        "service_account": service_account,
        "project_collection_path": project_collection_path,
        "project_id": project_id,
        "project_collection_id": project_collection_id,
        "tape_resource_location": tape_resource_location,
        "tape_resource": tape_resource,
        "project_resource": project_resource,
        "project_resource_children": total_project_resource_children,
    }
