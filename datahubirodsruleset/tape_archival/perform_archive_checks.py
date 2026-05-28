# Entire collection:
# /rules/tests/run_test.sh -r perform_archive_checks -a "/nlmumc/projects/P000000017/C000000001,dlinssen" -j -u service-surfarchive
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
    project_id, project_collection_id, project_collection_path, project_path = parse_project_collection_path(
        ctx, archival_path, "archive"
    )
    check_project_collection_exists(ctx, project_path, project_collection_path)

    archive_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_ARCHIVE.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    if not formatters.format_string_to_boolean(archive_enabled):
        error_message = f"Archiving is disabled for this project: '{project_path}'"
        ctx.callback.msiWriteRodsLog(error_message, 0)
        ctx.callback.msiExit("-1", error_message)

    tape_resource, project_resource = get_project_resources(ctx, project_path)
    check_resources_available(ctx, tape_resource, project_resource, "archiving")

    service_account = get_service_account(ctx, tape_resource)
    # The minimum file size criteria (in bytes)
    minimum_file_size = ctx.callback.getResourceAVU(tape_resource, "minimumFileSize", "", "0", "false")["arguments"][2]

    validate_caller_is_service_account(ctx, service_account, "Archiving")
    validate_no_active_process(ctx, project_collection_path, "archival")

    return {
        "service_account": service_account,
        "project_collection_path": project_collection_path,
        "project_id": project_id,
        "project_collection_id": project_collection_id,
        "tape_resource": tape_resource,
        "minimum_file_size": minimum_file_size,
    }
