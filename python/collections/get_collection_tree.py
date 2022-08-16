# /rules/tests/run_test.sh -r get_collection_tree -a "P000000014/C000000001/.metadata_versions"

@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_collection_tree(ctx, relative_path):
    """
    Lists the folders and files attributes at the input 'path'

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    relative_path : str
       Relative path to collection; e.g: P000000014/C000000001/.metadata_versions

    Returns
    -------
    dict
       The folders and files attributes at the requested path
    """

    import time

    output = []

    absolute_path = formatters.format_absolute_project_path(relative_path)

    # Get sub-folders
    for result in row_iterator("COLL_NAME, COLL_CREATE_TIME, COLL_MODIFY_TIME", "COLL_PARENT_NAME = '{}'".format(absolute_path), AS_LIST, ctx.callback):

        # Extract only the name of the subfolder from the full name/path
        name = result[0].rsplit('/', 1)[1]
        relative_collection_path = relative_path + "/" + name

        folder_node = {
            "name": name,
            "full_path": result[0],
            "path": relative_collection_path,
            "type": "folder",
            "size": "--",
            "rescname": "--",
            "ctime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result[1]))),
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result[2])))
        }

        output.append(folder_node)

    for result in row_iterator("DATA_NAME, DATA_SIZE, DATA_RESC_NAME, DATA_CREATE_TIME, DATA_MODIFY_TIME", "COLL_NAME = '{}'".format(absolute_path),
                               AS_LIST, ctx.callback):

        relative_data_path = relative_path + "/" + result[0]

        data_node = {
            "name": result[0],
            "path": relative_data_path,
            "type": "file",
            "size": result[1],
            "rescname": result[2],
            "offlineResource": result[2] == "arcRescSURF01",
            "ctime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result[3]))),
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result[4])))
        }

        output.append(data_node)

    return output
