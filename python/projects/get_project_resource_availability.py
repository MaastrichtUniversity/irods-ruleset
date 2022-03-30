@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def get_project_resource_availability(ctx, project_id, ingest="true", destination="false", archive="false"):
    """
    Get if a project's resource(s) is/are up

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The project id, ie 'P000000010'
    ingest: bool
        If we need to check the 'ingestResource' attribute of the project as well, default True
    destination: bool
        If we need to check the 'ingestResource' attribute of the project as well, default True
    archive: bool
        If we need to check the 'ingestResource' attribute of the project as well, default True

    Returns
    -------
    bool
        If the resource(s) to check are both not down, we return True
    """

    project_path = "/nlmumc/projects/{}".format(project_id)
    check_destination_resource = destination == "true"
    check_ingest_resource = ingest == "true"
    check_archive_resource = archive == "true"

    if not check_archive_resource and not check_ingest_resource and not check_destination_resource:
        ctx.callback.msiExit("-1", "At least one of the three check parameters needs to be true")

    ingest_status = False
    if check_ingest_resource:
        ingest_resource = ctx.callback.getCollectionAVU(project_path, "ingestResource", "", "", "true")["arguments"][2]
        ingest_status = get_resource_status(ctx, ingest_resource)

    destination_status = False
    if check_destination_resource:
        destination_resource = ctx.callback.getCollectionAVU(project_path, "resource", "", "", "true")["arguments"][2]
        destination_status = get_resource_status(ctx, destination_resource)

    archive_status = False
    if check_archive_resource:
        archive_resource = ctx.callback.getCollectionAVU(project_path, "archiveDestinationResource", "", "", "true")[
            "arguments"
        ][2]
        archive_status = get_resource_status(ctx, archive_resource)

    return (
        check_ingest_resource is ingest_status
        and check_destination_resource is destination_status
        and check_archive_resource is archive_status
    )


def get_resource_status(ctx, resource_name):
    for result in row_iterator(
        "RESC_STATUS",
        "RESC_NAME = '{}'".format(resource_name),
        AS_LIST,
        ctx.callback,
    ):
        return result[0] != "down"
