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
    rename_status = 0
    replicate_status = 0
    trim_status = 0
    project_path = "/nlmumc/projects/{}".format(project_id)
    destination_resource = ctx.callback.getCollectionAVU(project_path, "resource", "", "", "true")["arguments"][2]

    ingest_resource = "arcRescSURF01"
    # resource_query_iter = row_iterator(
    #     "DATA_RESC_NAME",
    #     "COLL_NAME = '{}'".format(source_collection),
    #     AS_LIST,
    #     ctx.callback,
    # )
    # for row in resource_query_iter:
    #     ingest_resource = row[0]
    # # TODO add check for ingest_resource

    ctx.callback.msiWriteRodsLog(
        "INFO: Start replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
    check_collection_replication(ctx, destination_collection, destination_resource)
    check_collection_trim(ctx, destination_collection, ingest_resource)

    # This query get all the sub-files inside the collection
    query_iter = row_iterator(
        "DATA_NAME, COLL_NAME", "COLL_NAME like '{}%'".format(source_collection), AS_LIST, ctx.callback
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

        # If the destination collection sub-folder doesn't exist, create it.
        create_destination_collection_sub_folder(ctx, destination_file_base_path, destination_collection)

        # Move the file to the destination location
        rename_status += rename_collection_data(ctx, source_file_full_path, destination_file_full_path)

        # if source_file_name in ("instance.json", "schema.json"):
        #     continue

        # Replicate to the project resource
        replicate_status += replicate_collection_data(ctx, destination_file_full_path, destination_resource)

        # Trim original ingest replica
        trim_status += trim_collection_data(ctx, destination_file_full_path, ingest_resource)

    ctx.callback.msiWriteRodsLog(
        "INFO: End replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
    return rename_status + replicate_status + trim_status


def create_destination_collection_sub_folder(ctx, destination_file_base_path, destination_collection):
    if destination_file_base_path != destination_collection + "/":
        try:
            # Check if the sub-folder exists
            ctx.callback.msiObjStat(destination_file_base_path, irods_types.RodsObjStat())
        except RuntimeError:
            ctx.callback.msiWriteRodsLog("DEBUG: \tCreate sub-folder: {}".format(destination_file_base_path), 0)
            ctx.callback.msiCollCreate(destination_file_base_path, 1, 0)


def rename_collection_data(ctx, source_file_full_path, destination_file_full_path):
    rename_status = 0
    try:
        ctx.callback.msiWriteRodsLog(
            "DEBUG: \tRename file '{}' to '{}'".format(source_file_full_path, destination_file_full_path),
            0,
        )
        ret_rename = ctx.callback.msiDataObjRename(source_file_full_path, destination_file_full_path, 0, 0)
        rename_status = ret_rename["arguments"][3]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("ERROR: \tRename failed for: {}".format(destination_file_full_path), 0)
        rename_status = 1
    if rename_status != 0:
        return 1
    return 0


def check_collection_replication(ctx, destination_collection, destination_resource):
    counter = {}
    # ctx.callback.msiWriteRodsLog("destination_collection: {}".format(destination_collection), 0)
    resource_query_iter = row_iterator(
        "DATA_RESC_HIER, COLL_NAME, DATA_NAME",
        "COLL_NAME like '{}%'".format(destination_collection),
        AS_LIST,
        ctx.callback,
    )
    for row in resource_query_iter:
        file_resource_hierarchy = row[0]
        data_path = row[1] + "/" + row[2]
        # ctx.callback.msiWriteRodsLog("file_resource_hierarchy: {}".format(file_resource_hierarchy), 0)
        # ctx.callback.msiWriteRodsLog("data_path: {}".format(data_path), 0)
        if data_path not in counter:
            counter[data_path] = 0
        if destination_resource in file_resource_hierarchy:
            counter[data_path] += 1
            # ctx.callback.msiWriteRodsLog("count: {}".format(str(counter)), 0)

    for data_path in counter:
        if counter[data_path] < 2:
            # ctx.callback.msiWriteRodsLog("data: {}".format(str(data_path)), 0)
            replicate_collection_data(ctx, data_path, destination_resource)


def replicate_collection_data(ctx, destination_file_full_path, destination_resource):
    replication_status = 0
    try:
        ctx.callback.msiWriteRodsLog("DEBUG: \tStart replication for: {}".format(destination_file_full_path), 0)
        # destination_resource = "blabla"
        ret_replication = ctx.callback.msiDataObjRepl(
            destination_file_full_path,
            "destRescName={}++++all=++++verifyChksum=++++numThreads=10".format(destination_resource),
            0,
        )
        replication_status = ret_replication["arguments"][2]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("ERROR: \tReplication failed for: {}".format(destination_file_full_path), 0)
        replication_status = 1
    if replication_status != 0:
        return 1
    return 0


def check_collection_trim(ctx, destination_collection, ingest_resource):
    resource_query_iter = row_iterator(
        "COLL_NAME, DATA_NAME",
        "COLL_NAME like '{}%' AND DATA_RESC_NAME = '{}'".format(destination_collection, ingest_resource),
        AS_LIST,
        ctx.callback,
    )
    for row in resource_query_iter:
        data_path = row[0] + "/" + row[1]
        trim_collection_data(ctx, data_path, ingest_resource)


def trim_collection_data(ctx, destination_file_full_path, ingest_resource):
    trim_status = 1
    try:
        ctx.callback.msiWriteRodsLog("DEBUG: \tStart to trim for: {}".format(destination_file_full_path), 0)
        ret_trim = ctx.callback.msiDataObjTrim(destination_file_full_path, ingest_resource, "null", "1", "null", 0)
        # msiDataObjTrim returns 1 if a replica is trimmed, 0 if nothing trimmed
        trim_status = ret_trim["arguments"][5]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("ERROR: \tTrim failed for: {}".format(destination_file_full_path), 0)
        trim_status = 2
    if trim_status != 1:
        return 1
    return 0
