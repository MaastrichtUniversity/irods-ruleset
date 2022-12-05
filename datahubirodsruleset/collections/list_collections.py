# /rules/tests/run_test.sh -r list_collections -a "/nlmumc/projects/P000000014" -j
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_collections(ctx, project_path):
    """
    Get a listing of all the project's collections

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        Project absolute path

    Returns
    -------
    list
        a json list of collections objects
    """
    # Files to exclude from the user uploaded files
    # How to extend the list: "'metadata.xml', 'foobar.json'"
    num_files_exclusion = "'metadata.xml'"

    project_id = formatters.get_project_id_from_project_path(project_path)

    # Initialize the collections dictionary
    project_collections = []

    proj_size = float(0)
    for proj_coll in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '" + project_path + "'", AS_LIST, ctx.callback):
        # Calculate size for entire project
        coll_size = float(ctx.callback.get_collection_size(proj_coll[0], "B", "none", "")["arguments"][3])
        proj_size = proj_size + coll_size

        # Initialize the collections dictionary
        project_collection = {}

        project_collection["id"] = proj_coll[0].split("/")[4]

        # Get AVUs
        project_collection["size"] = coll_size
        project_collection["title"] = ctx.callback.getCollectionAVU(proj_coll[0], "title", "", "", FALSE_AS_STRING)[
            "arguments"
        ][2]
        project_collection["creator"] = ctx.callback.getCollectionAVU(proj_coll[0], "creator", "", "", FALSE_AS_STRING)[
            "arguments"
        ][2]
        project_collection["PID"] = ctx.callback.getCollectionAVU(proj_coll[0], "PID", "", "", FALSE_AS_STRING)[
            "arguments"
        ][2]
        project_collection["numFiles"] = int(
            ctx.callback.getCollectionAVU(proj_coll[0], "numFiles", "", "0", FALSE_AS_STRING)["arguments"][2]
        )

        # Calculate the number of user uploaded files
        metadata_files = 0

        latest_version_number = ctx.callback.getCollectionAVU(
            proj_coll[0], "latest_version_number", "", "", FALSE_AS_STRING
        )["arguments"][2]

        if latest_version_number:
            metadata_files = (int(latest_version_number) * 2) + 2

        project_collection_path = formatters.format_project_collection_path(project_id, project_collection["id"])

        for row in row_iterator(
            "DATA_NAME",
            "COLL_NAME = '{}' AND DATA_NAME in ({})".format(project_collection_path, num_files_exclusion),
            AS_LIST,
            ctx.callback,
        ):
            if row:
                metadata_files = metadata_files + 1

        project_collection["numUserFiles"] = int(project_collection["numFiles"]) - metadata_files

        project_collections.append(project_collection)

    return project_collections
