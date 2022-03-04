@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_collection_size_per_resource(ctx, project):
    """
    Query the resource attribute for the files in a collection
    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project : str
        Project ID
    Returns
    -------
    """
    from collections import OrderedDict
    import re

    # create empty output dict
    output = OrderedDict()

    # create empty resources dictionary
    resources = {}
    # query resources (names) and their respective attributes (IDs)
    for row in row_iterator("RESC_NAME, RESC_ID", "", AS_LIST, ctx.callback):
        resources[row[1]] = row[0]

    # set collection path based on input
    project_path = "/nlmumc/projects/{}/%".format(project)
    total_sizes = {}
    for row in row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like 'dcat:byteSize' AND COLL_NAME like '{}'".format(project_path),
        AS_LIST,
        ctx.callback,
    ):
        collection_id = re.sub("^/nlmumc/projects/P[0-9]{9}/", "", row[0])
        total_sizes[collection_id] = row[1]

    # query size of collection per resource attribute (resource ID)
    for row in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like 'dcat:byteSize_resc%' AND COLL_NAME like '{}'".format(project_path),
        AS_LIST,
        ctx.callback,
    ):
        collection_id = re.sub("^/nlmumc/projects/P[0-9]{9}/", "", row[0])
        resource_id = re.sub("^dcat:byteSize_resc_", "", row[1])
        relative_size = (float(row[2]) / float(total_sizes[collection_id])) * 100
        result = {
            "resourceName": resources[resource_id],
            "resourceId": resource_id,
            "size": row[2],
            "relativeSize": round(relative_size, 1),
        }
        if collection_id in output:
            output[collection_id].append(result)
        else:
            output[collection_id] = [result]

    return output
