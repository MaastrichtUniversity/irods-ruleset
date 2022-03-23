@make(inputs=[0, 1, 2, 3, 4, 5], outputs=[6], handler=Output.STORE)
def create_drop_zone(ctx, dropzone_type, username, project_id, title, schema_name, schema_version):
    """
    Has to be run as 'RODS' for mounted collections

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    dropzone_type: str
        The type of dropzone to create, either 'mounted' or 'direct'
    username: str
        The creator of the dropzone
    schema_version: str
        The version of the schema that the dropzone was created for
    schema_name: str
        The name of the schema that the dropzone was created for
    title: str
        The title of the dropzone
    project_id: str
        The ID of the project to create a dropzone for

    Returns
    -------
    str
        The token of the created dropzone
    """

    # Generate a new token
    token = ctx.callback.generate_token("")["arguments"][0]

    # This is needed because the python rule returns a quoted string
    token_stripped = json.loads(token)

    # Format the path based on the dropzone type
    dropzone_path = format_dropzone_path(ctx, token_stripped, dropzone_type)
    if dropzone_type == "mounted":
        vo_person_external_id = ctx.callback.get_user_attribute_value(username, "voPersonExternalID", "true", "")[
            "arguments"
        ][3]
        vo_person_external_id = json.loads(vo_person_external_id)["value"]

    # Check if user has permissions to create dropzone
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, dropzone_type, "")["arguments"][2]
    if has_dropzone_permission == "false":
        # -818000 CAT_NO_ACCESS_PERMISSION
        ctx.callback.msiExit(
            "-818000",
            "User '{}' has insufficient DropZone permissions on for a dropzone of type '{}'".format(
                username, dropzone_type
            ),
        )

    # Check if the ingest resource is up
    ingest_resource_available = ctx.callback.get_project_resource_availability(
        project_id, "true", "false", "false", ""
    )["arguments"][4]
    if ingest_resource_available != "true":
        ctx.callback.msiExit(
            "-1", "Ingest resource is down for project '{}'! Aborting dropzone creation.".format(project_id)
        )

    # Create the dropzone
    status = ctx.callback.msiCollCreate(dropzone_path, 0, 0)["arguments"][2]
    if status != 0:
        ctx.callback.msiExit("-1", "Collection creation failed")

    # Set AVUs
    ctx.callback.setCollectionAVU(dropzone_path, "project", project_id)
    ctx.callback.setCollectionAVU(dropzone_path, "title", title)
    ctx.callback.setCollectionAVU(dropzone_path, "schemaName", schema_name)
    ctx.callback.setCollectionAVU(dropzone_path, "schemaVersion", schema_version)
    ctx.callback.setCollectionAVU(dropzone_path, "creator", username)
    ctx.callback.setCollectionAVU(dropzone_path, "state", "open")

    # Create the folder on the SMB share if mounted dropzone
    if dropzone_type == "mounted":
        ctx.callback.createRemoteDirectory(project_id, token_stripped, vo_person_external_id)

    # Set ACLs
    ctx.callback.msiSetACL("default", "own", username, dropzone_path)

    return token
