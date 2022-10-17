# /rules/tests/run_test.sh -r perform_irsync -a "handsome-snake,/nlmumc/projects/P000000019/C000000001,replRescUM01,dlinssen" -u "dlinssen"
@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, token, destination_collection, destination_resource, depositor):
    """
    This rule is part the mounted ingest workflow.

    In case of failed ingest and an admin want to restart the rule:
        * It MUST be done on the ingestion resource server (iRES-UM or iRES-AZM), NOT iCAT.
            * The rule needs physical access to the source collection to perform the 'irsync' call.
        * If the dropzone state AVU is 'error_ingestion', the rule 'finish_ingest' will be called afterward.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The dropzone token, to locate the source collection; e.g: 'handsome-snake'
    destination_collection: str
        The absolute path to the newly created project collection; e.g: '/nlmumc/projects/P000000018/C000000001'
    destination_resource: str
        The resource where the data objects will be replicated; e.g: 'replRescUM01'
    depositor: str
        The user who started the ingestion
    """
    from subprocess import CalledProcessError, check_call  # nosec
    import time

    source_collection = "/mnt/ingest/zones/{}".format(token)
    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    placeholder_instance_path = "{}/instance.json".format(source_collection)
    placeholder_schema_path = "{}/schema.json".format(source_collection)

    try:
        check_call(["rm", placeholder_instance_path], shell=False)
        check_call(["rm", placeholder_schema_path], shell=False)
    except CalledProcessError:
        ctx.callback.setErrorAVU(
            dropzone_path,
            "state",
            DropzoneState.ERROR_INGESTION.value,
            "Error while deleting metadata files placeholder '{}' or '{}'".format(
                placeholder_instance_path,
                placeholder_schema_path
            )
        )

    # Query dropzone state AVU and to call the rule finish_ingest if the state is 'error_ingestion' (= ingest restart)
    ingest_restart = False
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    if state == DropzoneState.ERROR_INGESTION.value:
        ingest_restart = True
        ctx.callback.msiWriteRodsLog("Restarting ingestion {}".format(dropzone_path), 0)
        ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)

    RETRY_MAX_NUMBER = 5
    RETRY_SLEEP_NUMBER = 20

    retry_counter = RETRY_MAX_NUMBER
    return_code = 0
    while retry_counter > 0:
        try:
            return_code = check_call(
                [
                    "irsync", "-K", "-v", "-R", destination_resource,
                    "-r", source_collection, "i:" + destination_collection
                ],
                shell=False
            )
        except CalledProcessError as err:
            ctx.callback.msiWriteRodsLog("ERROR: irsync: cmd '{}' retcode'{}'".format(err.cmd, err.returncode), 0)
            return_code = 1

        if return_code != 0:
            retry_counter -= 1
            ctx.callback.msiWriteRodsLog("DEBUG: Decrement irsync retry_counter: {}".format(str(retry_counter)), 0)
            time.sleep(RETRY_SLEEP_NUMBER)
        else:
            retry_counter = 0
            ctx.callback.msiWriteRodsLog("INFO: Ingest collection data '{}' was successful".format(source_collection), 0)

    if return_code != 0:
        ctx.callback.setErrorAVU(
            dropzone_path,
            "state",
            DropzoneState.ERROR_INGESTION.value,
            "Error while performing perform_irsync towards '{}:{}'".format(
                destination_collection,
                destination_resource
            )
        )

    if ingest_restart:
        project_id = formatters.get_project_id_from_project_collection_path(destination_collection)
        collection_id = formatters.get_collection_id_from_project_collection_path(destination_collection)

        ingest_resource = ctx.callback.getCollectionAVU(
            format_project_path(ctx, project_id), ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        ingest_resource_host = ""
        # Obtain the resource host from the specified ingest resource
        for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
            ingest_resource_host = row[0]

        ctx.callback.finish_ingest(project_id, depositor, token, collection_id, ingest_resource_host, "mounted")
