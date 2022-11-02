# /rules/tests/run_test.sh -r index_update_single_project_collection_metadata -a "P000000014,C000000001," -u service-disqover

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def index_update_single_project_collection_metadata(ctx, project_id, collection_id):
    """
    Use this rule to update a single project collection metadata (instance.json & AVUs) in the
    $COLLECTION_METADATA_INDEX.
       - connect to the $ELASTIC_HOST if no connection is provided
       - delete existing document
       - create a new document in the index

    Parameters
    ----------
    ctx : Context
       Combined type of callback and rei struct.
    project_id: str
        The project ID ie P000000001
    collection_id: str
        The collection ID ie C000000001
    es: Elasticsearch
        Connection to elastic search.

    Returns
    -------
    bool
        if the indexing was successful

    """
    from elasticsearch import ElasticsearchException

    es = get_elastic_search_connection(ctx)

    try:
        es.delete(index=COLLECTION_METADATA_INDEX, id=project_id + "_" + collection_id, ignore=[400, 404])
    except ElasticsearchException:
        message = "Unable to delete existing document"
        ctx.callback.writeLine("stdout", "ERROR: {}".format(message))
        ctx.callback.msiWriteRodsLog("ERROR: {}".format(message), 0)
        ctx.callback.msiWriteRodsLog("ERROR: ElasticsearchException raised during document deletion", 0)
        return False

    project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
    return index_project_collection(ctx, es, project_collection_path)
