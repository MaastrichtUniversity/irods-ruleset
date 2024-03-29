import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path


@make(inputs=range(3), outputs=[], handler=Output.STORE)
def perform_direct_ingest(ctx, project_id, depositor, token):
    """
    Perform a direct (collection to collection) ingest operation.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project id, e.g: P00000010
    depositor: str
        The iRODS username of the user who started the ingestion
    token: str
        The token of the dropzone to be ingested
    """
    import time

    RETRY_MAX_NUMBER = 5
    RETRY_SLEEP_NUMBER = 60

    dropzone_type = "direct"
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(project_id, dropzone_path, token, depositor, dropzone_type, "")[
            "arguments"
        ][5]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]
    ingest_resource_host = pre_ingest_results["ingest_resource_host"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    retry_counter = RETRY_MAX_NUMBER
    status = 0
    while retry_counter > 0:
        ret = ctx.callback.ingest_collection_data(dropzone_path, destination_collection, project_id, "")
        status = int(ret["arguments"][3])
        if status != 0:
            retry_counter -= 1
            ctx.callback.msiWriteRodsLog("DEBUG: Decrement retry_counter: {}".format(str(retry_counter)), 0)
            time.sleep(RETRY_SLEEP_NUMBER)
        else:
            retry_counter = 0
            ctx.callback.msiWriteRodsLog("INFO: Ingest collection data '{}' was successful".format(dropzone_path), 0)

    if status != 0:
        ctx.callback.set_ingestion_error_avu(dropzone_path, "Error copying ingest zone", project_id, depositor)

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(
        project_id, collection_id, dropzone_path, dropzone_type, str(difference), depositor
    )

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, depositor, token, collection_id, ingest_resource_host, dropzone_type)
