# /rules/tests/run_test.sh -r index_all_metadata -u service-disqover
@make(inputs=[], outputs=[], handler=Output.STORE)
def index_all_metadata(ctx):
    from elasticsearch import ElasticsearchException
    es = setup_elastic()

    total = 0
    success_count = 0
    message = "Index summary: {}/{} successful collection index done"

    try:
        es.indices.delete(index="irods", ignore=[400, 404])
    except ElasticsearchException:
        message = message.format(success_count, total)
        ctx.callback.writeLine("stdout", "ERROR: {}".format(message))
        ctx.callback.msiWriteRodsLog("ERROR: {}".format(message), 0)
        return

    # TODO try to get all Project ID & Collection ID
    # TODO STOP exec if instance.json doesn't exist
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

    instance_exists = True
    try:
        ctx.callback.msiObjStat(instance_path, irods_types.RodsObjStat())
    except RuntimeError:
        instance_exists = False
    if not instance_exists:
        return False

    instance = read_data_object_from_irods(ctx, instance_path)
    # TODO add try catch around json parsing
    instance_object = json.loads(instance)

    # AVU metadata
    project_title = ctx.callback.getCollectionAVU(project_path, "title", "", "", FALSE_AS_STRING)["arguments"][2]
    instance_object["project_title"] = project_title
    instance_object["project_id"] = project_id
    instance_object["collection_id"] = collection_id

    # TODO to the es.index & es.update in 1 call
    # TODO get status code of update ?
    # Instance json
    try:
        res = es.index(
            index="irods",
            id=project_id + "_" + collection_id,
            document=instance_object,
        )
    except ElasticsearchException:
        ctx.callback.writeLine("stdout", project_title)
        return False

    if res['result'] == "created":
        return True

    return False


def setup_elastic():
    from elasticsearch import Elasticsearch
    import os

    # TODO USE HTTPS
    # retry_on_timeout=True
    # max_retries=5
    ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')
    ELASTIC_URL = "elasticsearch.dh.local"  # TODO os.getenv('ELASTIC_URL')
    ELASTIC_PORT = "9200"
    es = Elasticsearch([{"host": ELASTIC_URL, "port": ELASTIC_PORT}],http_auth=("elastic", ELASTIC_PASSWORD))

    return es
