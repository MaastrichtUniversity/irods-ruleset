# /rules/tests/run_test.sh -r get_project_finance -a "/nlmumc/projects/P000000014" -u psuppers -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import in_conditions


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_finance(ctx, project_path):
    """
    Query the project financial information

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path : str
        The project absolute path

    Returns
    -------
    dict
        The project financial information
    """
    return get_projects_finance_details(ctx, [project_path])[project_path]


def get_projects_finance_details(ctx, project_paths):
    collections = {path: {} for path in project_paths}
    # Keep empty collections, and query only direct children of selected projects.
    for condition in in_conditions("COLL_PARENT_NAME", collections):
        for path, in row_iterator("COLL_NAME", condition, AS_LIST, ctx.callback):
            collections[path.rsplit("/", 1)[0]][path] = []
        for path, attribute, value in row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            condition + " AND META_COLL_ATTR_NAME like 'dcat:byteSize_resc_%'",
            AS_LIST,
            ctx.callback,
        ):
            collections[path.rsplit("/", 1)[0]][path].append((attribute, value))

    resources_prices = {}
    if any(sizes for project in collections.values() for sizes in project.values()):
        for resource_id, price in row_iterator(
            "RESC_ID, META_RESC_ATTR_VALUE", "META_RESC_ATTR_NAME = 'NCIT:C88193'", AS_LIST, ctx.callback
        ):
            resources_prices[resource_id] = price

    return {path: calculate_project_finance(project, resources_prices) for path, project in collections.items()}


def calculate_project_finance(collections, resources_prices):
    project_cost = 0
    project_size = 0
    project_collections_output = []

    for project_collection_path, sizes in collections.items():
        collection_cost = 0
        collection_size = 0
        resources_details = []

        for collection_result in sizes:
            resource_id = collection_result[0].replace("dcat:byteSize_resc_", "")
            collection_size_on_resource = float(collection_result[1])

            price_per_gb_per_year = float(resources_prices[resource_id])

            # Convert to GB (for calculation and display of costs)
            size_on_resource = collection_size_on_resource / 1000 / 1000 / 1000
            collection_size = collection_size + collection_size_on_resource

            # Calculate cost
            storage_cost_on_resource = size_on_resource * price_per_gb_per_year
            collection_cost = collection_cost + storage_cost_on_resource

            # Store the collection finance information for each resource
            details = {
                "resource": resource_id,
                "data_size_gb_on_resource": size_on_resource,
                "price_per_gb_per_year": price_per_gb_per_year,
                "storage_cost_on_resource": storage_cost_on_resource,
            }
            resources_details.append(details)

        # Convert to GiB
        collection_size = float(collection_size) / 1024 / 1024 / 1024

        # Store the overall collection finance information
        project_collection = {
            "collection": project_collection_path,
            "data_size_gib": collection_size,
            "details_per_resource": resources_details,
            "collection_storage_cost": collection_cost,
        }
        project_collections_output.append(project_collection)

        project_cost = project_cost + collection_cost
        project_size = project_size + collection_size

    project_size_gib = project_size
    project_size_gb = project_size * (1.024**3)

    project_cost_yearly = project_cost
    project_cost_monthly = project_cost / 12

    # Store the overall project finance information
    output = {
        "project_cost_yearly": project_cost_yearly,
        "project_cost_monthly": project_cost_monthly,
        "collections": project_collections_output,
        "project_size_gib": project_size_gib,
        "project_size_gb": project_size_gb,
    }
    return output
