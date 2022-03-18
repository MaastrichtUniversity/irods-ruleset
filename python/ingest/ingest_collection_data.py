@make(inputs=range(3), outputs=[], handler=Output.STORE)
def ingest_collection_data(ctx, source_collection, destination_collection, project_id):
    """
    Ingest the input source collection toward the destination collection.
    Ingest:
        * Create the destination collection sub-folders, if required
        * Rename individually each files inside the source collection to the destination collection
            - Not renaming the whole source collection to preserve the dropzone folder and its AVU (e.g: state, etc ...)
        * Replicate each files inside the destination collection to the project resource
        * Trim each files original replica at the input ingest resource

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    source_collection: str
        The absolute path of the source collection/dropzone
    destination_collection: str
        The absolute path of the destination project collection
    project_id: str
        The project id, ie P00000010
    """
    project_path = "/nlmumc/projects/{}".format(project_id)
    destination_resource = ctx.callback.getCollectionAVU(project_path, "resource", "", "", "true")["arguments"][2]

    # TODO add check instance.json exist
    ingest_resource = ""
    resource_query_iter = row_iterator(
        "DATA_RESC_NAME",
        "COLL_NAME = '{}' AND DATA_NAME = 'instance.json'".format(source_collection),
        AS_LIST,
        ctx.callback,
    )
    for row in resource_query_iter:
        ingest_resource = row[0]
    # TODO add check for ingest_resource

    # This query get all the sub-files inside the collection
    ctx.callback.msiWriteRodsLog(
        "INFO: Start replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
    query_iter = row_iterator(
        "DATA_NAME, COLL_NAME", "COLL_NAME like '" + source_collection + "%' ", AS_LIST, ctx.callback
    )
    for row in query_iter:
        source_file_name = row[0]
        source_file_base_path = row[1]
        source_file_full_path = source_file_base_path + "/" + source_file_name

        # Build destination paths. Example:
        # source_file_base_path = /nlmumc/ingest/direct/crazy-frog/sub1
        # source_collection = /nlmumc/ingest/direct/crazy-frog
        # sub_folder_path = /sub1
        sub_folder_path = source_file_base_path.replace(source_collection, "")
        destination_file_base_path = destination_collection + sub_folder_path
        destination_file_full_path = destination_file_base_path + "/" + source_file_name

        # Check if the sub-folder exists
        if destination_file_base_path != destination_collection + "/":
            try:
                ctx.callback.msiObjStat(destination_file_base_path, irods_types.RodsObjStat())
            except RuntimeError:
                ctx.callback.msiWriteRodsLog("DEBUG: \tCreate sub-folder: {}".format(destination_file_base_path), 0)
                ctx.callback.msiCollCreate(destination_file_base_path, 1, 0)

        # Move the source collection to the destination location
        ctx.callback.msiWriteRodsLog(
            "DEBUG: \tRename file '{}' to '{}'".format(source_file_full_path, destination_file_full_path),
            0,
        )
        ret_rename = ctx.callback.msiDataObjRename(source_file_full_path, destination_file_full_path, 0, 0)
        rename_status = ret_rename["arguments"][3]
        if rename_status != 0:
            ctx.callback.setErrorAVU(source_collection, "state", "error-ingestion", "Error during msiDataObjRename")

        # Replicate to project resource
        replication_status = 0
        try:
            ctx.callback.msiWriteRodsLog("DEBUG: \tStart replication for: {}".format(destination_file_full_path), 0)
            # destination_resource = "blabla"
            ret_replication = ctx.callback.msiDataObjRepl(
                destination_file_full_path, "destRescName={}".format(destination_resource), 0
            )
            replication_status = ret_replication["arguments"][2]
        except RuntimeError:
            ctx.callback.msiWriteRodsLog("ERROR: \tReplication failed for: {}".format(destination_file_full_path), 0)
            ctx.callback.setErrorAVU(
                destination_collection,
                "state",
                "error-ingestion",
                "Error while replicating {}".format(destination_file_full_path),
            )
        if replication_status != 0:
            ctx.callback.setErrorAVU(
                destination_collection,
                "state",
                "error-ingestion",
                "Error while replicating {}".format(destination_file_full_path),
            )

        # TODO Add retry mechanism??

        # Trim original ingest replica
        ctx.callback.msiWriteRodsLog("DEBUG: \tStart trimming for: {}".format(destination_file_full_path), 0)
        ret_trim = ctx.callback.msiDataObjTrim(destination_file_full_path, ingest_resource, "null", "1", "null", 0)
        trim_status = ret_trim["arguments"][5]
        # Trim success status = 1
        if trim_status != 1:
            ctx.callback.setErrorAVU(
                destination_collection,
                "state",
                "error-ingestion",
                "Error while trimming {}".format(destination_file_full_path),
            )

    ctx.callback.msiWriteRodsLog(
        "INFO: End replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
