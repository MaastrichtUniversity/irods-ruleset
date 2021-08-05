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
    # set collection path based on input
    project_path = "/nlmumc/projects/{}/%".format(project)

    # create empty output list
    output = []

    # query size of collection per resource attribute (resource ID)
    for row in row_iterator("COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                            "META_COLL_ATTR_NAME like 'dcat:byteSize_resc%' AND COLL_NAME like '{}'".format(project_path),
                            AS_LIST,
                            ctx.callback):
        result = dict(collection=row[0], resourceAttr=row[1][19:], size=row[2])
        output.append(result)

    # create empty values dictionary
    values = {}

    # query resources (names) and their respective attributes (IDs)
    for row in row_iterator("RESC_NAME, RESC_ID",
                            "",
                            AS_LIST,
                            ctx.callback):

        values[row[1]] = row[0]

    # append resources (names) to output based on attributes (IDs)
    for i in range(len(output)):
        output[i]["resource"] = values[output[i]["resourceAttr"]]

    return output

