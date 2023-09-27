# /rules/tests/run_test.sh -r optimized_list_collections -a "/nlmumc/projects/P000000014" -j
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def optimized_list_collections(ctx, project_path):
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

    for proj_coll in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '" + project_path + "'", AS_LIST, ctx.callback):
        # Initialize the collections dictionary
        project_collection = {}
        project_collection["size"] = 0
        project_collection["title"] = ""
        project_collection["creator"] = ""
        project_collection["PID"] = ""
        project_collection["numFiles"] = 0
        project_collection["id"] = formatters.get_collection_id_from_project_collection_path(proj_coll[0])

        parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
        conditions = "META_COLL_ATTR_NAME in ('dcat:byteSize', 'title', 'creator', 'PID', 'numFiles', 'latest_version_number') AND COLL_NAME = '{}' ".format(
            proj_coll[0]
        )
        latest_version_number = ""
        for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
            # Loop over metadata
            if result[1] == "dcat:byteSize":
                project_collection["size"] = int(result[2])
            if result[1] == "title":
                project_collection["title"] = result[2]
            if result[1] == "creator":
                project_collection["creator"] = result[2]
            if result[1] == "PID":
                project_collection["PID"] = result[2]
            if result[1] == "numFiles":
                project_collection["numFiles"] = int(result[2])
            if result[1] == "latest_version_number":
                latest_version_number = result[2]

        # Calculate the number of user uploaded files
        metadata_files = 0

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
