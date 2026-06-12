import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path


@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_ingest(ctx, project_id, depositor, token, dropzone_type):
    """
    Perform an ingest operation.

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
    dropzone_type: str
        The type of dropzone to be ingested (mounted or direct)
    """
    import time

    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)

    pre_ingest_results = json.loads(
        ctx.callback.perform_ingest_pre_hook(project_id, dropzone_path, token, depositor, dropzone_type, "")[
            "arguments"
        ][5]
    )
    collection_id = pre_ingest_results["collection_id"]
    destination_collection = pre_ingest_results["destination_collection"]

    # Determine pre-ingest time to calculate average ingest speed
    before = time.time()

    # Ingest the files from local directory on resource server (mounted) or a iRODS virtual collection to iRODS destination collection
    try:
        ctx.callback.sync_collection_data(token, destination_collection, depositor, dropzone_type)
    except RuntimeError:
        # sync_collection_data already set the dropzone state to 'error-ingestion'.
        # Do NOT call set_ingestion_error_avu here: that function calls msiExit("-1", ...)
        # which would terminate execution and prevent perform_ingest_post_hook and
        # finish_ingest from running. For mounted ingests, perform_irsync retries
        # internally on the resource server; a transient connection drop causes
        # remoteExec to raise RuntimeError on icat even though the data may have been
        # synced successfully. Allowing execution to continue lets finish_ingest
        # complete the ingest when the data is present, or let downstream error
        # handling (set_post_ingestion_error_avu) report a genuine failure.
        ctx.callback.msiWriteRodsLog(
            f"WARNING: sync_collection_data raised an error for {dropzone_path}, continuing with post-ingest steps", 0
        )
        # replace_metadata_placeholder_files is normally called by sync_collection_data
        # on its success path (after the try/except). Since we caught an exception here,
        # sync_collection_data exited early and never called it. For mounted ingests the
        # irsync may still have succeeded (false-negative remoteExec disconnect), so
        # call it here to ensure the metadata files are replaced before finish_ingest.
        # For a genuine irsync failure it is called optimistically; validate_data_post_ingestion
        # inside perform_ingest_post_hook will catch the actual missing-data condition.
        if dropzone_type == "mounted":
            ctx.callback.replace_metadata_placeholder_files(token, project_id, collection_id, depositor)

    after = time.time()
    difference = float(after - before) + 1

    ctx.callback.perform_ingest_post_hook(
        project_id, collection_id, dropzone_path, dropzone_type, str(difference), depositor
    )

    # Handle post ingestion operations
    ctx.callback.finish_ingest(project_id, depositor, token, collection_id, dropzone_type)
