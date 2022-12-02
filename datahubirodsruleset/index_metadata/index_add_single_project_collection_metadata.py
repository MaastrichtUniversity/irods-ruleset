# /rules/tests/run_test.sh -r index_add_single_project_collection_metadata -a "P000000014,C000000001" -u service-disqover
from dhpythonirodsutils import formatters

from datahubirodsruleset.index_metadata.index_all_project_collections_metadata import index_project_collection
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import get_elastic_search_connection


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def index_add_single_project_collection_metadata(ctx, project_id, collection_id):
    """
    Use this rule to index a single project collection metadata (instance.json & AVUs) into the
    $COLLECTION_METADATA_INDEX. project collection should not be indexed already
       - connect to the $ELASTIC_HOST
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
        True, if the indexing was successful. Otherwise, false
    """
    es = get_elastic_search_connection(ctx)
    project_collection_path = formatters.format_project_collection_path(project_id, collection_id)

    index_success = index_project_collection(ctx, es, project_collection_path)
    if not index_success:
        error_message = "ERROR: Elasticsearch update index failed for {}".format(project_collection_path)
        ctx.callback.msiWriteRodsLog(error_message, 0)

    return index_success
