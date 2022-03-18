@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def validate_dropzone(ctx, dropzone_path, username):
    """
    Validate if the dropzone and depositor are eligible for ingestion by:
        - Check if user has dropzone permissions
        - Check if depositor is the creator of the dropzone (only in direct ingest)
        - Check if the dropzone exists
        - Check if the linked project ID exists
        - Check if the state is OK
        - Validate the metadata
        - Get necessary AVU's and return them

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path: str
        The token, e.g. '/nlmumc/ingest/direct/crazy-frog' or '/nlmumc/ingest/zones/crazy-frog'
    username: str
        The username of the depositor, e.g. dlinssen
    """
    # Check if ingesting user has dropzone permissions
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, "")["arguments"][1]
    if has_dropzone_permission != "true":
        ctx.callback.msiExit(
            "-818000", "User '{}' has insufficient DropZone permissions on '{}'".format(username, dropzone_path)
        )

    # Check if dropzone exists
    try:
        ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    # If direct ingest: check if user ingesting is the creator
    if "direct" in dropzone_path:
        creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", "true")["arguments"][2]
        if creator != username:
            ctx.callback.msiExit(
                "-818000", "User '{}' is not the creator of dropzone '{}'".format(username, dropzone_path)
            )

    # Get dropzone metadata
    project_id = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", "true")["arguments"][2]

    # Check if project path exists
    try:
        ctx.callback.msiObjStat("/nlmumc/projects/{}".format(project_id), irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown project: {}".format(project_id))

    title = ctx.callback.getCollectionAVU(dropzone_path, "title", "", "", "true")["arguments"][2]
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", "true")["arguments"][2]

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

    ctx.callback.msiWriteRodsLog("Starting validation of {}:".format(dropzone_path), 0)
    # Set 'state' AVU to 'validating'
    ctx.callback.setCollectionAVU(dropzone_path, "state", "validating")

    validation_result = ctx.callback.validate_metadata(dropzone_path, "")["arguments"][1]
    return {"project_id": project_id, "title": title, "validation_result": validation_result}
