@make(inputs=range(4), outputs=[], handler=Output.STORE)
def perform_direct_ingest(ctx, source_collection, destination_collection, ingest_resource, project_id):
    """
    Perform an ingest from the input source collection to the destination collection.
    Ingest:
        * Rename the input source collection to the destination collection
        * Replicate each files inside the destination collection to the project resource
        * Trim each files original replica at the input ingest resource

    Parameters
    ----------
    ctx
    source_collection: str
        The absolute path of the source collection/dropzone
    destination_collection: str
        The absolute path of the destination project collection
    ingest_resource: str
        The name of the ingestion resource
    project_id: str
        The project id, ie P00000010
    """
    # Move the source collection to the destination location
    ctx.callback.msiWriteRodsLog(
        "INFO: Rename drop-zone '{}' to project collection '{}'".format(source_collection, destination_collection), 0
    )
    rename_status = ctx.callback.msiDataObjRename(source_collection, destination_collection, 1, 0)["arguments"][3]
    # ctx.callback.msiWriteRodsLog("INFO: rename_status '{}'".format(rename_status), 0)
    if rename_status != 0:
        ctx.callback.setErrorAVU(source_collection, "state", "error-ingestion", "Error during msiDataObjRename")

    project_path = "/nlmumc/projects/{}".format(project_id)
    destination_resource = ctx.callback.getCollectionAVU(project_path, "resource", "", "", "true")["arguments"][2]

    ctx.callback.msiWriteRodsLog(
        "INFO: Start replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
    # This query get all the sub-files inside the collection
    query_iter = row_iterator(
        "DATA_NAME, COLL_NAME", "COLL_NAME like '" + destination_collection + "%' ", AS_LIST, ctx.callback
    )
    for row in query_iter:
        file_name = row[0]
        file_base_path = row[1]
        file_full_path = file_base_path + "/" + file_name

        # Replicate to project resource
        ctx.callback.msiWriteRodsLog("DEBUG: \tStart replication for: {}".format(file_full_path), 0)
        ret_replication = ctx.callback.msiDataObjRepl(file_full_path, "destRescName={}".format(destination_resource), 0)
        replication_status = ret_replication["arguments"][2]
        if replication_status != 0:
            ctx.callback.setErrorAVU(
                destination_collection, "state", "error-ingestion", "Error while replicating {}".format(file_full_path)
            )

        # TODO Add retry mechanism??

        # Trim original ingest replica
        ctx.callback.msiWriteRodsLog("DEBUG: \tStart trimming for: {}".format(file_full_path), 0)
        ret_trim = ctx.callback.msiDataObjTrim(file_full_path, ingest_resource, "null", "1", "null", 0)
        trim_status = ret_trim["arguments"][5]
        # Trim success status = 0
        if trim_status != 1:
            ctx.callback.setErrorAVU(
                destination_collection, "state", "error-ingestion", "Error while trimming {}".format(file_full_path)
            )

    ctx.callback.msiWriteRodsLog(
        "INFO: End replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
