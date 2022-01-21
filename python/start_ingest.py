@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def start_ingest(ctx, username, token):
    """
    Start an ingest

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    username: str
        The username, ie 'dlinssen'
    token: str
        The token, ie 'crazy-frog'

    Returns
    -------
    list
        a json list of projects objects
    """
    source_collection = "/nlmumc/ingest/zones/{}".format(token)

    # Check if ingesting user has dropzone permissions
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, "")["arguments"][1]
    if has_dropzone_permission != "true" and has_dropzone_permission is not True:
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
    if project_id == "":
        ctx.callback.msiExit("-1", "No project number on dropzone")

    title = ctx.callback.getCollectionAVU(source_collection, "title", "", "", "true")["arguments"][2]
    state = ctx.callback.getCollectionAVU(source_collection, "state", "", "", "true")["arguments"][2]
    project_resource = ctx.callback.getCollectionAVU(
        "/nlmumc/projects/{}".format(project_id), "resource", "", "", "true"
    )["arguments"][2]

    # Get resource availability
    resources_available_json = ctx.callback.list_destination_resources_status("")["arguments"][0]
    irods_resources_available = json.loads(resources_available_json)
    available = False
    for irods_resource in irods_resources_available:
        if irods_resource["name"] == project_resource:
            available = irods_resource["available"]
            break

    # Ingest resource is not available, abort ingest
    if not available:
        # -831000 CAT_INVALID_RESOURCE
        ctx.callback.msiExit("-831000", "Ingest disabled for this resource.")

    # Check for valid state to start ingestion
    if state != "open" and state != "warning-validation-incorrect":
        ctx.callback.msiExit("-1", "Invalid state to start ingestion.")

    ctx.callback.msiWriteRodsLog("Starting validation of {}:".format(source_collection), 0)
    # Set 'state' AVU to 'validating'
    ctx.callback.setCollectionAVU(source_collection, "state", "validating")

    validation_result = ctx.callback.validate_metadata(source_collection, "")["arguments"][1]
    if validation_result:
        ctx.callback.msiWriteRodsLog(
            "Validation result OK {}. Setting status to 'in-queue-for-ingestion'".format(source_collection), 0
        )
        ctx.delayExec(
            "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF>",
            "perform_ingest('{}', '{}', '{}', '{}')".format(project_id, title, username, token),
            "",
        )
    else:
        ctx.callback.setErrorAVU(source_collection, "state", "warning-validation-incorrect", "Metadata is incorrect")
