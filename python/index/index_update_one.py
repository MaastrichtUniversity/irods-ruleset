# /rules/tests/run_test.sh -r index_update_one -a "P000000014,C000000002" -u service-disqover
@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def index_update_one(ctx, project_id, collection_id):
    es = setup_elastic()

    es.delete(index="irods", id=project_id + "_" + collection_id)
    index_project_collection(ctx, es, project_id, collection_id)
