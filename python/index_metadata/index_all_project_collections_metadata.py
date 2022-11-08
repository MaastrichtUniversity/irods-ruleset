# /rules/tests/run_test.sh -r index_all_project_collections_metadata -u service-disqover
@make(inputs=[], outputs=[], handler=Output.STORE)
def index_all_project_collections_metadata(ctx):
    """
    Use this rule to re-create $COLLECTION_METADATA_INDEX with all project collection metadata (instance.json & AVUs):
        - Connect to the $ELASTIC_HOST
        - Delete the current elastic search index $COLLECTION_METADATA_INDEX
        - Query all project collection metadata
        - For each project collection metadata, create a new index document

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    """
    from elasticsearch import ElasticsearchException

    es = get_elastic_search_connection(ctx)

    total = 0
    success_count = 0
    message = "Index summary: {}/{} successful collection index done"

    try:
        es.indices.delete(index=COLLECTION_METADATA_INDEX, ignore=[400, 404])
    except ElasticsearchException:
        message = message.format(success_count, total)
        ctx.callback.writeLine("stdout", "ERROR: {}".format(message))
        ctx.callback.msiWriteRodsLog("ERROR: {}".format(message), 0)
        ctx.callback.msiWriteRodsLog("ERROR: ElasticsearchException raised during index deletion", 0)
        return

    parameters = "COLL_NAME"
    conditions = "COLL_NAME like '/nlmumc/projects/P_________/C_________' AND DATA_NAME = 'instance.json'"
    for row in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        total += 1
        project_collection_path = row[0]

        successful_index = index_project_collection(ctx, es, project_collection_path)
        if successful_index:
            success_count += 1

    message = message.format(success_count, total)
    ctx.callback.writeLine("stdout", message)
    ctx.callback.msiWriteRodsLog("DEBUG: {}".format(message), 0)


def index_project_collection(ctx, es, project_collection_path):
    from elasticsearch import ElasticsearchException

    project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
    collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
    project_path = formatters.format_project_path(project_id)
    instance_path = formatters.format_instance_collection_path(project_id, collection_id)

    try:
        ctx.callback.msiObjStat(instance_path, irods_types.RodsObjStat())
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("ERROR: msiObjStat RuntimeError raised for {}".format(project_collection_path), 0)
        return False

    instance = read_data_object_from_irods(ctx, instance_path)
    try:
        instance_object = json.loads(instance)
    except ValueError:
        ctx.callback.msiWriteRodsLog("ERROR: JSONDecodeError raised for {}".format(project_collection_path), 0)
        return False

    # AVU metadata
    project_title = ctx.callback.getCollectionAVU(project_path, ProjectAVUs.TITLE.value, "", "", FALSE_AS_STRING)[
        "arguments"
    ][2]
    project_access_info = json.loads(ctx.callback.get_project_user_members(project_id, "")["arguments"][1])

    instance_object["project_title"] = project_title
    instance_object["project_id"] = project_id
    instance_object["collection_id"] = collection_id
    instance_object["user_access"] = project_access_info["users"]
    instance_object["group_display_names"] = project_access_info["group_display_names"]
    instance_object["user_display_names"] = project_access_info["user_display_names"]

    try:
        res = es.index(
            index=COLLECTION_METADATA_INDEX,
            id=project_id + "_" + collection_id,
            document=instance_object,
        )
    except ElasticsearchException:
        ctx.callback.msiWriteRodsLog("ERROR: ElasticsearchException raised for {}".format(project_collection_path), 0)
        return False

    if "result" in res and res["result"] == "created":
        return True

    ctx.callback.msiWriteRodsLog("ERROR: Collection metadata indexing failed for {}".format(project_collection_path), 0)
    return False
