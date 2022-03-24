@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def start_ingest(ctx, username, token, dropzone_type):
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
        The username, eg 'dlinssen'
    token: str
        The token, eg 'crazy-frog'
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'
    """
    if dropzone_type == "mounted":
        dropzone_path = "/nlmumc/ingest/zones/{}".format(token)
    elif dropzone_type == "direct":
        dropzone_path = "/nlmumc/ingest/direct/{}".format(token)
    else:
        ctx.callback.msiExit(
            "-1", "Invalid dropzone type, supported 'mounted' and 'direct', got '{}'.".format(dropzone_type)
        )

    pre_ingest_tasks = json.loads(
        ctx.callback.validate_dropzone(dropzone_path, username, dropzone_type, "")["arguments"][3]
    )
    project_id = pre_ingest_tasks["project_id"]
    title = pre_ingest_tasks["title"]
    validation_result = pre_ingest_tasks["validation_result"]

    if validation_result == "true":
        ctx.callback.msiWriteRodsLog(
            "Validation result OK {}. Setting status to 'in-queue-for-ingestion'".format(dropzone_path), 0
        )
        ctx.callback.setCollectionAVU(dropzone_path, "state", "in-queue-for-ingestion")

        ctx.delayExec(
            "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF>",
            "perform_{}_ingest('{}', '{}', '{}', '{}')".format(dropzone_type, project_id, title, username, token),
            "",
        )
    else:
        ctx.callback.setErrorAVU(dropzone_path, "state", "warning-validation-incorrect", "Metadata is incorrect")
