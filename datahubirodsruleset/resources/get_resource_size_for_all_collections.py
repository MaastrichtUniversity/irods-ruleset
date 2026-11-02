from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error


from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_resource_size_for_all_collections(ctx):
    """
    OPS report rule.
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

    project_ids = {
        formatters.get_project_id_from_project_path(path)
        for path, in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback)
    }
    if not project_ids:
        return {}

    resource_names = {
        resource_id: name
        for name, resource_id in row_iterator("RESC_NAME, RESC_ID", "", AS_LIST, ctx.callback)
    }
    prices = {}
    for name, price in row_iterator(
        "RESC_NAME, META_RESC_ATTR_VALUE", "META_RESC_ATTR_NAME = 'NCIT:C88193'", AS_LIST, ctx.callback
    ):
        prices[name] = price

    # Fetch the cached per-resource sizes once, without the collection-size
    # helper's repeated resource queries and unused percentage calculations.
    resources = {}
    for path, attribute, size in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like 'dcat:byteSize_resc%' AND COLL_NAME like '/nlmumc/projects/%/%'",
        AS_LIST,
        ctx.callback,
    ):
        if path.split("/")[3] not in project_ids:
            continue
        name = resource_names[attribute.removeprefix("dcat:byteSize_resc_")]
        if name not in resources:
            resources[name] = {"size": 0}
        resources[name]["size"] += int(size)

    for resource in resources:
        cost_of_resource = prices.get(resource) or "0"
        cost_per_year = (
            float(resources[resource]["size"]) / 1000 / 1000 / 1000 * float(cost_of_resource)
        )
        resources[resource]["cost_per_year"] = round(cost_per_year, 2)
        resources[resource]["cost_per_month"] = round(cost_per_year / 12, 2)
    return resources
