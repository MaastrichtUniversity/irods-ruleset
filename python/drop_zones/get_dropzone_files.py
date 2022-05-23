# /rules/tests/run_test.sh -r get_dropzone_tree -a "vast-dove"
@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_dropzone_files(ctx, token, directory):
    """
    Lists the folders and files attributes at the input 'path'

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token : str
       The dropzone token
    directory: str
        The directory to list the files of

    Returns
    -------
    dict
       The folders and files attributes at the requested path
    """

    import time

    output = {"files": [], "folders": []}
    absolute_path = "/nlmumc/ingest/direct/{}{}".format(token, directory)
    dropzone_path = "/nlmumc/ingest/direct/{}".format(token)

    if absolute_path[-1] == "/":
        absolute_path = absolute_path[:-1]


    for result in row_iterator("DATA_NAME, DATA_SIZE, DATA_RESC_NAME, DATA_CREATE_TIME, DATA_MODIFY_TIME, COLL_NAME", "COLL_NAME = '{}'".format(absolute_path),
                               AS_LIST, ctx.callback):

        relative_data_path = result[5] + "/" + result[0]
        relative_data_path = relative_data_path.replace(dropzone_path, "")

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

        output["files"].append(data_node)

    for result in row_iterator("COLL_NAME, COLL_CREATE_TIME, COLL_MODIFY_TIME", "COLL_PARENT_NAME = '{}'".format(absolute_path), AS_LIST, ctx.callback):

        # Extract only the name of the subfolder from the full name/path
        name = result[0].rsplit('/', 1)[1]
        relative_collection_path = result[0].replace("/nlmumc/ingest/direct/{}".format(token), "")

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

        output["folders"].append(folder_node)

    return output
