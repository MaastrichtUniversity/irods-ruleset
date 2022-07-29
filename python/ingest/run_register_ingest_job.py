# /rules/tests/run_test.sh -r run_register_ingest_job -a "/tmp/src_dir,/nlmumc/home/rods/reg_coll"

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def run_register_ingest_job(ctx, source_directory, target_collection):
    from subprocess import check_call, CalledProcessError

    # raise CalledProcessError(retcode, cmd)
    # "/tmp/src_dir", "/nlmumc/home/rods/reg_coll"
    return_code = None
    try:
        return_code = check_call(["/opt/irods/run_ingest_job.sh", source_directory, target_collection])
    except CalledProcessError as err:
        # ctx.callback.msiWriteRodsLog("INFO: run_ingest_job: cmd '{}' retcode'{}'".format(err.cmd, err.returncode), 0)
        ctx.callback.msiExit("-1", "ERROR: run_ingest_job: cmd '{}' retcode'{}'".format(err.cmd, err.returncode))

    ctx.callback.msiWriteRodsLog("INFO: run_ingest_job: return_code '{}'".format(return_code), 0)
