# /rules/tests/run_test.sh -r index_update_single_project_collection_metadata -a "P000000014,C000000001" -u service-disqover
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import get_elastic_search_connection, COLLECTION_METADATA_INDEX
from datahubirodsruleset.index_metadata.index_all_project_collections_metadata import index_project_collection


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
        The project ID e.g: P000000001
    collection_id: str
        The collection ID e.g: C000000001

    Returns
    -------
    bool
        True, if the indexing was successful
    """
    from elasticsearch import ElasticsearchException

    es = get_elastic_search_connection(ctx)

    project_collection_path = formatters.format_project_collection_path(project_id, collection_id)
    error_message = "ERROR: Elasticsearch update index failed for {}".format(project_collection_path)

    try:
        es.delete(index=COLLECTION_METADATA_INDEX, id=project_id + "_" + collection_id, ignore=[400, 404])
    except ElasticsearchException:
        ctx.callback.msiWriteRodsLog("ERROR: ElasticsearchException raised during document deletion", 0)
        ctx.callback.msiWriteRodsLog(error_message, 0)
        return False

    index_success = index_project_collection(ctx, es, project_collection_path)
    if not index_success:
        ctx.callback.msiWriteRodsLog(error_message, 0)

    return index_success
