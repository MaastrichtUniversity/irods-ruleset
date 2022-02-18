@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def start_ingest(ctx, username, token):
    """
    Start an ingest
       Irods pre-ingest checks
       Metadata pre-ingest checks
        If those went well, call perform ingest

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username: str
        The username, ie 'dlinssen'
    token: str
        The token, ie 'crazy-frog'
    """
    source_collection = "/nlmumc/ingest/zones/{}".format(token)

    # Check if ingesting user has dropzone permissions
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, "")["arguments"][1]
    if has_dropzone_permission != "true":
        ctx.callback.msiExit(
            "-818000", "User '{}' has insufficient DropZone permissions on /nlmumc/ingest/zones".format(username)
        )

    # Check if dropzone exists
    try:
        ctx.callback.msiObjStat(source_collection, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    # Get dropzone metadata
    project_id = ctx.callback.getCollectionAVU(source_collection, "project", "", "", "true")["arguments"][2]

    # Check if project path exists
    try:
        ctx.callback.msiObjStat("/nlmumc/projects/{}".format(project_id), irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown project: {}".format(project_id))

    title = ctx.callback.getCollectionAVU(source_collection, "title", "", "", "true")["arguments"][2]
    state = ctx.callback.getCollectionAVU(source_collection, "state", "", "", "true")["arguments"][2]

    # Get resource availability -- check ingest & destination resource
    available = ctx.callback.get_project_resource_availability(project_id, "true", "true", "false", "")["arguments"][4]
    # Project or ingest resource is not available, abort ingest
    if available != "true":
        # -831000 CAT_INVALID_RESOURCE
        ctx.callback.msiExit(
            "-831000", "The project or ingest resource is disabled for this project '{}'".format(project_id)
        )

    # Check for valid state to start ingestion
    if state != "open" and state != "warning-validation-incorrect":
        ctx.callback.msiExit("-1", "Invalid state to start ingestion.")

    ctx.callback.msiWriteRodsLog("Starting validation of {}:".format(source_collection), 0)
    # Set 'state' AVU to 'validating'
    ctx.callback.setCollectionAVU(source_collection, "state", "validating")

    validation_result = ctx.callback.validate_metadata(source_collection, "")["arguments"][1]
    if validation_result == "true":
        ctx.callback.msiWriteRodsLog(
            "Validation result OK {}. Setting status to 'in-queue-for-ingestion'".format(source_collection), 0
        )
        ctx.callback.setCollectionAVU(source_collection, "state", "in-queue-for-ingestion")
        ctx.delayExec(
            "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF>",
            "perform_ingest('{}', '{}', '{}', '{}')".format(project_id, title, username, token),
            "",
        )
    else:
        ctx.callback.setErrorAVU(source_collection, "state", "warning-validation-incorrect", "Metadata is incorrect")
