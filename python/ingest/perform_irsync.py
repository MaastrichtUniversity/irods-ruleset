@make(inputs=range(3), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, token, destination_collection, destination_resource):
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
            ctx.callback.msiWriteRodsLog("DEBUG: Decrement retry_counter: {}".format(str(retry_counter)), 0)
            time.sleep(RETRY_SLEEP_NUMBER)
        else:
            retry_counter = 0
            ctx.callback.msiWriteRodsLog("INFO: Ingest collection data '{}' was successful".format(source_collection), 0)

    if return_code != 0:
        ctx.callback.setErrorAVU(
            dropzone_path, "state", DropzoneState.ERROR_INGESTION.value, "Error copying ingest zone"
        )

