# /rules/tests/run_test.sh -r index_update_single_project_metadata -a "P000000014" -u service-disqover
import json

from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def index_update_single_project_metadata(ctx, project_id):
    """
    Use this rule to update all collection metadata (instance.json & AVUs) in the
    $COLLECTION_METADATA_INDEX that belong to a specific project
        - connect to the $ELASTIC_HOST
        - list collections for the project
        - for each collection
            - update document in the index

    Parameters
    ----------
    ctx : Context
      Combined type of callback and rei struct.
    project_id: str
       The project ID e.g: P000000001
    """
    project_path = formatters.format_project_path(project_id)
    collections = json.loads(ctx.callback.list_collections(project_path, "")["arguments"][1])

    for collection in collections:
        collection_id = collection["id"]
        ctx.callback.index_update_single_project_collection_metadata(project_id, collection_id, "")
