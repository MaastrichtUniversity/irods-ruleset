from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_collection_path
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING


@make(inputs=[0, 1, 2, 3, 4, 5], outputs=[], handler=Output.STORE)
def perform_ingest_post_hook(ctx, project_id, collection_id, source_collection, dropzone_type, difference, depositor):
    """
    This rule is part the ingestion workflow.
    Perform the common tasks for both 'mounted' and 'direct' post-ingest.

    Parameters
    ----------
    ctx: Context
         Combined type of callback and rei struct.
    project_id: str
        The project id, e.g: P00000010
    collection_id: str
        The collection id, e.g: C00000001
    source_collection: str
        The absolute path of the source collection/dropzone
    dropzone_type: str
        The type of dropzone: direct or mounted.
    difference: str
        Time difference between the start and the end of the data ingestion.
    depositor: str
        The user who started the ingestion
    """
    destination_project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    # Calculate and set the byteSize and numFiles AVU. false/false because collection
    # is already open and needs to stay open
    ctx.callback.setCollectionSize(project_id, collection_id, FALSE_AS_STRING, FALSE_AS_STRING)
    collection_num_files = ctx.callback.getCollectionAVU(
        destination_project_collection_path, "numFiles", "", "", TRUE_AS_STRING
    )["arguments"][2]
    collection_size = ctx.callback.getCollectionAVU(
        destination_project_collection_path, "dcat:byteSize", "", "", TRUE_AS_STRING
    )["arguments"][2]

    avg_speed = float(collection_size) / 1024 / 1024 / float(difference)
    size_gib = float(collection_size) / 1024 / 1024 / 1024

    ctx.callback.msiWriteRodsLog(
        "{} : Ingested {} GiB in {} files".format(source_collection, size_gib, collection_num_files), 0
    )
    ctx.callback.msiWriteRodsLog("{} : Sync took {} seconds".format(source_collection, difference), 0)
    ctx.callback.msiWriteRodsLog("{} : AVG speed was {} MiB/s".format(source_collection, avg_speed), 0)

    ctx.callback.validate_data_post_ingestion(
        destination_project_collection_path, source_collection, dropzone_type, depositor
    )
