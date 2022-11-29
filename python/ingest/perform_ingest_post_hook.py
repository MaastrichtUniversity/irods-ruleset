@make(inputs=[0, 1, 2, 3, 4], outputs=[], handler=Output.STORE)
def perform_ingest_post_hook(ctx, project_id, collection_id, source_collection, dropzone_type, difference):
    destination_project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    # Calculate and set the byteSize and numFiles AVU. false/false because collection
    # is already open and needs to stay open
    ctx.callback.setCollectionSize(project_id, collection_id, FALSE_AS_STRING, FALSE_AS_STRING)
    collection_num_files = ctx.callback.getCollectionAVU(destination_project_collection_path, "numFiles", "", "", TRUE_AS_STRING)["arguments"][2]
    collection_size = ctx.callback.getCollectionAVU(destination_project_collection_path, "dcat:byteSize", "", "", TRUE_AS_STRING)["arguments"][2]

    avg_speed = float(collection_size) / 1024 / 1024 / float(difference)
    size_gib = float(collection_size) / 1024 / 1024 / 1024

    ctx.callback.msiWriteRodsLog("{} : Ingested {} GiB in {} files".format(source_collection, size_gib, collection_num_files), 0)
    ctx.callback.msiWriteRodsLog("{} : Sync took {} seconds".format(source_collection, difference), 0)
    ctx.callback.msiWriteRodsLog("{} : AVG speed was {} MiB/s".format(source_collection, avg_speed), 0)

    # Compare drop-zone & project collection content
    instance_file_name = "instance.json"
    schema_file_name = "schema.json"

    # Dropzone
    if dropzone_type == "mounted":
        ret = ctx.callback.get_data_object_size(source_collection, instance_file_name, "")["arguments"][2]
        dropzone_instance_size = int(ret)
        ret = ctx.callback.get_data_object_size(source_collection, schema_file_name, "")["arguments"][2]
        dropzone_schema_size = int(ret)

        ctx.callback.msiWriteRodsLog("DEBUG: '{}' dropzone_instance_size: {}".format(source_collection, str(dropzone_instance_size)), 0)
        ctx.callback.msiWriteRodsLog("DEBUG: '{}' dropzone_schema_size: {}".format(source_collection, str(dropzone_schema_size)), 0)

    # Project collection
    ret = ctx.callback.get_data_object_size(destination_project_collection_path, instance_file_name, "")["arguments"][2]
    collection_instance_size = int(ret)
    ret = ctx.callback.get_data_object_size(destination_project_collection_path, schema_file_name, "")["arguments"][2]
    collection_schema_size = int(ret)

    ctx.callback.msiWriteRodsLog("DEBUG: '{}' collection_instance_size: {}".format(destination_project_collection_path, str(collection_instance_size)), 0)
    ctx.callback.msiWriteRodsLog("DEBUG: '{}' collection_schema_size: {}".format(destination_project_collection_path, str(collection_schema_size)), 0)
    ctx.callback.msiWriteRodsLog("DEBUG: '{}' collection_total_size: {}".format(destination_project_collection_path, str(collection_size)), 0)
    ctx.callback.msiWriteRodsLog("DEBUG: '{}' collection_file_count: {}".format(destination_project_collection_path, str(collection_num_files)), 0)

    dropzone_num_files = ctx.callback.getCollectionAVU(source_collection, "numFiles", "", "", TRUE_AS_STRING)["arguments"][2]
    dropzone_size = ctx.callback.getCollectionAVU(source_collection, "totalSize", "", "", TRUE_AS_STRING)["arguments"][2]

    match_num_files = int(dropzone_num_files) == int(collection_num_files)
    match_size = False
    if dropzone_type == "mounted":
        collection_user_size = int(collection_size) - int(collection_instance_size) - int(collection_schema_size)
        match_size = int(dropzone_size) == collection_user_size
    elif dropzone_type == "direct":
        match_size = int(dropzone_size) == int(collection_size)

    ctx.callback.msiWriteRodsLog("DEBUG: Match source_collection '{}' to '{}' size: {}".format(source_collection, destination_project_collection_path, str(match_size)), 0)
    ctx.callback.msiWriteRodsLog("DEBUG: Match source_collection '{}' to '{}' file_count: {}".format(source_collection, destination_project_collection_path, str(match_num_files)), 0)

    if match_size is False or match_num_files is False:
        ctx.callback.setErrorAVU(source_collection, "state", DropzoneState.ERROR_INGESTION.value, "Error copying data")
