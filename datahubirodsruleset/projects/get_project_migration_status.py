# /rules/tests/run_test.sh -r get_project_migration_status -a "/nlmumc/projects/P000000014" -u psuppers -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output, FALSE_AS_STRING, TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_migration_status(ctx, project_path):
    """
    Get the list of all the ongoing migration status

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        Project absolute path

    Returns
    -------
    list
        a json list of migration cards
    """
    # Initialize the cards list
    cards = []

    for proj_coll in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '{}'".format(project_path), AS_LIST, ctx.callback):
        collection = proj_coll[0]
        card = {
            "collection": collection.split("/")[4],
            "title": ctx.callback.getCollectionAVU(collection, "title", "", "", TRUE_AS_STRING)["arguments"][2],
        }

        archive = ctx.callback.getCollectionAVU(collection, "archiveState", "", "", FALSE_AS_STRING)["arguments"][2]
        if archive != "":
            new_card = card.copy()
            new_card["repository"] = "SURFSara Tape"
            new_card["status"] = archive
            cards.append(new_card)

        exporter = ctx.callback.getCollectionAVU(collection, "exporterState", "", "", FALSE_AS_STRING)["arguments"][2]
        if exporter != "":
            new_card = card.copy()
            status_split = exporter.split(":")
            new_card["repository"] = status_split[0]
            new_card["status"] = status_split[1]
            cards.append(new_card)

    return cards
