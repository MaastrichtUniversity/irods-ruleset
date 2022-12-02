# /rules/tests/run_test.sh -r get_project_resource_availability -a "P000000014,true,false,false" -j
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, format_project_path, Output, TRUE_AS_STRING, FALSE_AS_STRING


@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def get_project_resource_availability(ctx, project_id, ingest=TRUE_AS_STRING, destination=FALSE_AS_STRING, archive=FALSE_AS_STRING):
    """
    Get if a project's resource(s) is/are up

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project id, e.g: 'P000000010'
    ingest: str
        If we need to check the 'ingestResource' attribute of the project as well, default true
    destination: str
        If we need to check the 'resource' attribute of the project as well, default true
    archive: str
        If we need to check the 'archiveDestinationResource' attribute of the project as well, default true

    Returns
    -------
    bool
        If the resource(s) to check are both not down, we return True
    """

    project_path = format_project_path(ctx, project_id)
    check_destination_resource = formatters.format_string_to_boolean(destination)
    check_ingest_resource = formatters.format_string_to_boolean(ingest)
    check_archive_resource = formatters.format_string_to_boolean(archive)

    if not check_archive_resource and not check_ingest_resource and not check_destination_resource:
        ctx.callback.msiExit("-1", "At least one of the three check parameters needs to be true")

    ingest_status = False
    if check_ingest_resource:
        ingest_resource = ctx.callback.getCollectionAVU(
            project_path, ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        ingest_status = get_resource_status(ctx, ingest_resource)

    destination_status = False
    if check_destination_resource:
        destination_resource = ctx.callback.getCollectionAVU(project_path, ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING)["arguments"][2]
        destination_status = get_resource_status(ctx, destination_resource)

    archive_status = False
    if check_archive_resource:
        archive_resource = ctx.callback.getCollectionAVU(
            project_path, ProjectAVUs.ARCHIVE_DESTINATION_RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        archive_status = get_resource_status(ctx, archive_resource)

    return (
        check_ingest_resource is ingest_status
        and check_destination_resource is destination_status
        and check_archive_resource is archive_status
    )


# TODO move to its own file
def get_resource_status(ctx, resource_name):
    for result in row_iterator(
        "RESC_STATUS",
        "RESC_NAME = '{}'".format(resource_name),
        AS_LIST,
        ctx.callback,
    ):
        return result[0] != "down"
