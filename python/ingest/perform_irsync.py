# /rules/tests/run_test.sh -r perform_irsync -a "handsome-snake,/nlmumc/projects/P000000019/C000000001,replRescUM01" -u "dlinssen"
@make(inputs=range(3), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, token, destination_collection, destination_resource):
    """
    This rule is part the mounted ingest workflow.

    In case of failed ingest and an admin want to restart the rule:
        * It MUST be done on the ingestion resource server (iRES-UM or iRES-AZM), NOT iCAT.
            * The rule needs physical access to the source collection to perform the 'irsync' call.
        * When the rule have been successfully executed, the rule 'finish_ingest' still MUST be executed.

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
    """
    from subprocess import CalledProcessError, check_call  # nosec
    import time

    source_collection = "/mnt/ingest/zones/{}".format(token)
    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    RETRY_MAX_NUMBER = 5
    RETRY_SLEEP_NUMBER = 5

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

