# /rules/tests/run_test.sh -r index_update_project -a "P000000014" -u service-disqover
@make(inputs=[0], outputs=[], handler=Output.STORE)
def index_update_project(ctx, project_id):
    print("index_update_project: " + project_id)
    es = setup_elastic()

    project_path = formatters.format_project_path(project_id)
    collections = json.loads(ctx.callback.list_collections(project_path, "")["arguments"][1])
    for collection in collections:
        collection_id = collection["id"]
        es.delete(index="irods", id=project_id + "_" + collection_id)
        index_project_collection(ctx, es, project_id, collection_id)
