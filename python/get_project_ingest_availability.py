@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_ingest_availability(ctx, project_id, check_destination_resource="true"):
    """
    Get if a project's resource(s) is/are up to create/start an ingest

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id: str
        The project id, ie 'P000000010'
    check_destination_resource: bool
        If we need to check the 'resource' attribute of the project as well, default True

    Returns
    -------
    bool
        If the resource(s) to check are both not down, we return True
    """

    project_path = "/nlmumc/projects/{}".format(project_id)
    check_destination_resource = check_destination_resource == "true"

    ingest_resource = ctx.callback.getCollectionAVU(project_path, "ingestResource", "", "", "true")["arguments"][2]

    for result in row_iterator(
        "RESC_STATUS",
        "RESC_NAME = '{}'".format(ingest_resource),
        AS_LIST,
        ctx.callback,
    ):
        ingest_resource_available = result[0] != "down"

    if check_destination_resource:
        destination_resource = ctx.callback.getCollectionAVU(project_path, "resource", "", "", "true")["arguments"][2]
        ctx.callback.msiWriteRodsLog("{}".format(destination_resource), 0)
        for result in row_iterator(
            "RESC_STATUS",
            "RESC_NAME = '{}'".format(destination_resource),
            AS_LIST,
            ctx.callback,
        ):
            destination_resource_available = result[0] != "down"
            ctx.callback.msiWriteRodsLog("{}".format(destination_resource_available), 0)

    return (
        ingest_resource_available and destination_resource_available
        if check_destination_resource
        else ingest_resource_available
    )
