# /rules/tests/run_test.sh -r perform_irsync -a "handsome-snake,/nlmumc/projects/P000000019/C000000001,dlinssen" -u "dlinssen"
@make(inputs=range(3), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, token, destination_collection, depositor):
    """
    This rule is part the mounted ingest workflow.
    It takes care of coping (syncing) the content of the physical drop-zone path into the destination collection.
    When the coping is done, it also calls replace_metadata_placeholder_files to update the project collection
    with the correct metadata files.

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
    depositor: str
        The user who started the ingestion
    """
    # Suppress [B404:blacklist] Consider possible security implications associated with subprocess module.
    # subprocess is only use for subprocess.check_call to execute irsync.
    # The irsync checkcall has 3 variable inputs:
    # * destination_resource, queried directly from iCAT with getCollectionAVU ProjectAVUs.RESOURCE
    # * source_collection, token is validated with format_dropzone_path & check the ACL with getCollectionAVU state
    # * destination_collection, validated with the formatter functions get_*_from_project_collection_path
    from subprocess import CalledProcessError, check_call  # nosec
    import time

    source_collection = "/mnt/ingest/zones/{}".format(token)
    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    project_id = formatters.get_project_id_from_project_collection_path(destination_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(destination_collection)

    destination_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]

    # Query dropzone state AVU and to call the rule finish_ingest if the state is 'error_ingestion' (= ingest restart)
    ingest_restart = False
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    if state == DropzoneState.ERROR_INGESTION.value:
        ingest_restart = True
        ctx.callback.msiWriteRodsLog("Restarting ingestion {}".format(dropzone_path), 0)
        ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)

    remove_script_path = "/var/lib/irods/msiExecCmd_bin/remove-ingest-zone-access.sh"
    creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
    # ctx.callback.msiWriteRodsLog("creator ingestion {}".format(creator), 0)
    ret = ctx.callback.get_user_attribute_value(creator, "voPersonExternalID", TRUE_AS_STRING, "")[
        "arguments"
    ][3]
    vo_person_external_id = json.loads(ret)["value"]
    # ctx.callback.msiWriteRodsLog("vo_person_external_id ingestion {}".format(vo_person_external_id), 0)
    return_code = check_call([remove_script_path, vo_person_external_id,  source_collection], shell=False)
    # ctx.callback.msiWriteRodsLog("return_code remove_script_path {}".format(return_code), 0)

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

    ctx.callback.replace_metadata_placeholder_files(token, project_id, collection_id, depositor)

    if ingest_restart:
        ingest_resource = ctx.callback.getCollectionAVU(
            format_project_path(ctx, project_id), ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        ingest_resource_host = ""
        # Obtain the resource host from the specified ingest resource
        for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
            ingest_resource_host = row[0]

        ctx.callback.finish_ingest(project_id, depositor, token, collection_id, ingest_resource_host, "mounted")
