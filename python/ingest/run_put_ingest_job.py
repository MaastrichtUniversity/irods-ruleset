# /rules/tests/run_test.sh -r run_put_ingest_job -a "/tmp/src_dir,/nlmumc/home/rods/put_coll"

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def run_put_ingest_job(ctx, token, target_collection):
    from subprocess import check_call, CalledProcessError
    import os

    source_directory = '/mnt/ingest/zones/{}'.format(token)

    dropzone_path = format_dropzone_path(ctx, token, "mounted")

    total_size = 0
    for dir_path, dir_names, filenames in os.walk(source_directory):
        for f in filenames:
            fp = os.path.join(dir_path, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    ctx.callback.msiWriteRodsLog("INFO: run_put_ingest_job: totalSize '{}'".format(total_size), 0)

    ctx.callback.setCollectionAVU(dropzone_path, "totalSize", str(total_size))

    event_handler = "/opt/irods/event_handler_replRescUM01_put.py"
    return_code = None
    try:
        return_code = check_call(
            ["/opt/irods/run_put_ingest_job.sh", source_directory, target_collection, event_handler]
        )
    except CalledProcessError as err:
        ctx.callback.msiExit("-1", "ERROR: run_put_ingest_job: cmd '{}' retcode'{}'".format(err.cmd, err.returncode))

    ctx.callback.msiWriteRodsLog("INFO: run_put_ingest_job: return_code '{}'".format(return_code), 0)
