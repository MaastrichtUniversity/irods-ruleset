from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_resource_size_for_all_collections(ctx):
    """
    HAS TO BE CALLED AS RODSADMIN.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    List
        The resources that data is stored on and the amount of data stored on them.
        This includes replicated resources (so that amount is already doubled!)
    """

    resources = {}
    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback):
        project_path = result[0]
        project_id = formatters.get_project_id_from_project_path(project_path)
        collection_size_per_resource = json.loads(ctx.callback.get_collection_size_per_resource(project_id, "")["arguments"][1])
        collection = collection_size_per_resource.values()
        for collection_resources in collection:
            for collection_resource in collection_resources:
                if collection_resource["resourceName"] not in resources:
                    resources[collection_resource["resourceName"]] = int(collection_resource["size"])
                else:
                    resources[collection_resource["resourceName"]] += int(collection_resource["size"])
    return resources
