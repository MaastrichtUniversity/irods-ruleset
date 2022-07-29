# /rules/tests/run_test.sh -r remote_run_ingest_job -a "/tmp/src_dir,/nlmumc/home/rods/put_coll,ires.dh.local"

@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def remote_run_ingest_job(ctx, token, target_collection, ingest_resource_host):
    rule_code = """
    run_put_ingest_job("{token}", "{target_collection}")
    """.format(token=token, target_collection=target_collection)

    ctx.callback.remoteExec(ingest_resource_host, '', rule_code, '')
