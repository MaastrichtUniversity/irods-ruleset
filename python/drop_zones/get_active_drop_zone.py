@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_active_drop_zone(ctx, token, check_ingest_resource_status):
    """
    Get the attribute values for an active dropzone

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    token : str
        The dropzone token
    check_ingest_resource_status : str
        'true'/'false' expected; If true, query the project resource status

    Returns
    -------
    dict
        The attribute values
    """
    username = ctx.callback.get_client_username("")["arguments"][0]
    dropzone_path = "/nlmumc/ingest/zones/" + token

    # Check if the user has right access at /nlmumc/ingest/zones
    # TODO: Make check dynamic
    ret = ctx.callback.checkDropZoneACL(username, "mounted", "*has_dropzone_permission")
    has_dropzone_permission = ret["arguments"][1]
    if has_dropzone_permission == "false":
        msg = "User '{}' has insufficient DropZone permissions on /nlmumc/ingest/zones".format(username)
        # -818000 CAT_NO_ACCESS_PERMISSION
        ctx.callback.msiExit("-818000", msg)

    # Check if the dropzone exist
    try:
        ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    project_path = ""
    # Initialize the output
    avu = {
        "state": "",
        "title": "",
        "validateState": "",
        "validateMsg": "",
        "project": "",
        "projectTitle": "",
        "date": "",
        "token": token,
        "resourceStatus": "",
        "totalSize": "0",
        "destination": "",
    }
    # Query the dropzone metadata
    for result in row_iterator(
        "COLL_MODIFY_TIME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}'".format(dropzone_path),
        AS_LIST,
        ctx.callback,
    ):
        attr_name = result[1]
        attr_value = result[2]

        if attr_name == "project":
            avu[attr_name] = attr_value
            avu["date"] = result[0]
            project_path = "/nlmumc/projects/{}".format(attr_value)
            for project_result in row_iterator(
                "META_COLL_ATTR_VALUE",
                "META_COLL_ATTR_NAME = 'title' AND " "COLL_NAME = '{}'".format(project_path),
                AS_LIST,
                ctx.callback,
            ):
                avu["projectTitle"] = project_result[0]
        else:
            avu[attr_name] = attr_value

    if check_ingest_resource_status == "true":
        # Query project resource avu
        resource = ctx.callback.getCollectionAVU(project_path, "resource", "*resource", "", "true")["arguments"][2]
        # Query the resource status
        for resc_result in row_iterator("RESC_STATUS", "RESC_NAME = '{}'".format(resource), AS_LIST, ctx.callback):
            avu["resourceStatus"] = resc_result[0]

    return avu
