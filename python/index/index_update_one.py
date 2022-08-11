# /rules/tests/run_test.sh -r index_update_one -a "P000000014,C000000002" -u service-disqover
@make(inputs=[0,1], outputs=[], handler=Output.STORE)
def index_update_one(ctx, project_id, collection_id):
    from elasticsearch import Elasticsearch

    es = Elasticsearch([{"host": "elasticsearch.dh.local", "port": "9200"}], http_auth=('elastic', 'foobar'))

    es.delete(index="irods", id=project_id + "_" + collection_id)

    project_path = formatters.format_project_path(project_id)
    project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
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
    project_title = ctx.callback.getCollectionAVU(project_path, "title", "", "", FALSE_AS_STRING)["arguments"][
        2
    ]
    doc["project_title"] = project_title
    doc["project_id"] = project_id
    doc["collection_id"] = collection_id
    es.update(
        index="irods",
        id=project_id + "_" + collection_id,
        body={"doc": doc},
    )

