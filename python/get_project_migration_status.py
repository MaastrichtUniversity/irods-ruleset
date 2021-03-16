@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_migration_status(ctx, project_path):
    """
    Get the list of all the ongoing migration status

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_path: str
        Project absolute path

    Returns
    -------
    list
        a json list of migration cards
    """
    # Initialize the cards list
    cards = []

    for proj_coll in row_iterator("COLL_NAME",
                                  "COLL_PARENT_NAME = '{}'".format(project_path),
                                  AS_LIST,
                                  ctx.callback):
        card = {}
        collection = proj_coll[0]

        card["collection"] = collection.split("/")[4]
        card["title"] = ctx.callback.getCollectionAVU(collection, "title", "", "", "true")["arguments"][2]

        ret = ctx.callback.getCollectionAVU(collection, "archiveState", "", "", "false")["arguments"][2]
        if ret != '':
            card["repository"] = "SURFSara Tape"
            card["status"] = ret
            cards.append(card)

        ret = ctx.callback.getCollectionAVU(collection, "exporterState", "", "", "false")["arguments"][2]
        if ret != '':
            status_split = ret.split(':')
            card["repository"] = status_split[0]
            card["status"] = status_split[1]
            cards.append(card)

    return cards
