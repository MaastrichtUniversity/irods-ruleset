# /rules/tests/run_test.sh -r run_put_ingest_job -a "/tmp/src_dir,/nlmumc/home/rods/put_coll"

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def run_put_ingest_job(ctx, token, target_collection):
    import os
    import requests

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

    url = 'http://irods-ingest-worker.dh.local:5000/job'
    data = {"source": source_directory, "target": target_collection}
    try:
        r = requests.post(url, json=data)
        r.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        ctx.callback.msiWriteRodsLog("ERROR: run_put_ingest_job: request '{}'".format(errh), 0)
        ctx.callback.msiExit("-1", "ERROR: run_put_ingest_job: cmd '{}' retcode'{}'".format(data, errh))
    except requests.exceptions.ConnectionError as errc:
        ctx.callback.msiWriteRodsLog("ERROR: run_put_ingest_job: request '{}'".format(errc), 0)
        ctx.callback.msiExit("-1", "ERROR: run_put_ingest_job: cmd '{}' retcode'{}'".format(data, errc))
    except requests.exceptions.Timeout as errt:
        ctx.callback.msiWriteRodsLog("ERROR: run_put_ingest_job: request '{}'".format(errt), 0)
        ctx.callback.msiExit("-1", "ERROR: run_put_ingest_job: cmd '{}' retcode'{}'".format(data, errt))
    except requests.exceptions.RequestException as err:
        ctx.callback.msiWriteRodsLog("ERROR: run_put_ingest_job: request '{}'".format(err), 0)
        ctx.callback.msiExit("-1", "ERROR: run_put_ingest_job: cmd '{}' retcode'{}'".format(data, err))

    ctx.callback.msiWriteRodsLog("INFO: run_put_ingest_job: return_code '{}'".format(r.status_code), 0)
