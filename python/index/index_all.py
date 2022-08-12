# /rules/tests/run_test.sh -r index_all -a "true" -u service-disqover
@make(inputs=[0], outputs=[], handler=Output.STORE)
def index_all(ctx, remove_index):
    es = setup_elastic()

    if formatters.format_string_to_boolean(remove_index):
        es.indices.delete(index="irods", ignore=[400, 404])

    projects = json.loads(ctx.callback.list_projects_minimal("")["arguments"][0])
    for project in projects:
        project_id = str(project["id"])
        project_path = formatters.format_project_path(project_id)
        collections = json.loads(ctx.callback.list_collections(project_path, "")["arguments"][1])
        for collection in collections:
            collection_id = collection["id"]
            index_project_collection(ctx, es, project_id, collection_id)


def index_project_collection(ctx, es, project_id, collection_id):
    project_path = formatters.format_project_path(project_id)
    instance_path = formatters.format_instance_collection_path(project_id, collection_id)

    instance_exists = True
    try:
        ctx.callback.msiObjStat(instance_path, irods_types.RodsObjStat())
    except RuntimeError:
        instance_exists = False
    if instance_exists:
        instance = read_data_object_from_irods(ctx, instance_path)
        instance_object = json.loads(instance)

        # Instance json
        es.index(
            index="irods",
            id=project_id + "_" + collection_id,
            document=instance_object,
        )

    # AVU metadata
    doc = {}
    project_title = ctx.callback.getCollectionAVU(project_path, "title", "", "", FALSE_AS_STRING)["arguments"][2]
    doc["project_title"] = project_title
    doc["project_id"] = project_id
    doc["collection_id"] = collection_id
    doc["user_access"] = json.loads(ctx.callback.get_all_users_with_access_to_project(project_id, "")["arguments"][1])
    es.update(
        index="irods",
        id=project_id + "_" + collection_id,
        body={"doc": doc},
    )


def setup_elastic():
    from elasticsearch import Elasticsearch

    es = Elasticsearch([{"host": "elasticsearch.dh.local", "port": "9200"}], http_auth=("elastic", "foobar"))

    return es
