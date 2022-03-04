@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_finance(ctx, project_path):
    """
    Query the project financial information

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_path : str
        The project absolute path

    Returns
    -------
    dict
        The project financial information
    """
    project_cost = 0
    project_size = 0
    resources_prices = {}
    collections_output = []

    # Get all project's collections
    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '{}'".format(project_path), AS_LIST, ctx.callback):
        # collections.append(result[0])

        collection_path = result[0]
        collection_cost = 0
        collection_size = 0
        resources_details = []

        # Get the collection size on each resources
        parameters = "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
        conditions = "META_COLL_ATTR_NAME like 'dcat:byteSize_resc_%' AND COLL_NAME = '{}'".format(collection_path)
        for collection_result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
            resource_id = collection_result[0].replace("dcat:byteSize_resc_", "")
            collection_size_on_resource = float(collection_result[1])

            query_resource_price = True
            # Check resources_prices before even querying iCAT
            if resource_id in resources_prices:
                query_resource_price = False

            # Only query if price_per_gb_per_year(NCIT:C88193) was not found in resources_prices
            if query_resource_price:
                for resource_result in row_iterator(
                    "META_RESC_ATTR_VALUE",
                    "RESC_ID = '{}' and META_RESC_ATTR_NAME = 'NCIT:C88193'".format(resource_id),
                    AS_LIST,
                    ctx.callback,
                ):
                    resources_prices[resource_id] = resource_result[0]
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
        collection = {
            "collection": collection_path,
            "data_size_gib": collection_size,
            "details_per_resource": resources_details,
            "collection_storage_cost": collection_cost,
        }
        collections_output.append(collection)

        project_cost = project_cost + collection_cost
        project_size = project_size + collection_size

    project_size_gib = project_size
    project_size_gb = project_size * (1.024 ** 3)

    project_cost_yearly = project_cost
    project_cost_monthly = project_cost / 12

    # Store the overall project finance information
    output = {
        "project_cost_yearly": project_cost_yearly,
        "project_cost_monthly": project_cost_monthly,
        "collections": collections_output,
        "project_size_gib": project_size_gib,
        "project_size_gb": project_size_gb,
    }
    return output
