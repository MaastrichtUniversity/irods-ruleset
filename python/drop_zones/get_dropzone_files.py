# /rules/tests/run_test.sh -r get_dropzone_files -a "crazy-frog,/tmp"
@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_dropzone_files(ctx, token, directory):
    """
    Lists the folders and files attributes at the input 'directory'

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token : str
       The dropzone token
    directory: str
        The directory to list the folders and files of

    Returns
    -------
    list
       The folders and files attributes at the requested path
    """

    import time

    output = []
    dropzone_path = "/nlmumc/ingest/direct/{}".format(token)
    absolute_path = "{}{}".format(dropzone_path, directory)

    if absolute_path[-1] == "/":
        absolute_path = absolute_path[:-1]

    for result in row_iterator("COLL_NAME, COLL_CREATE_TIME",
                               "COLL_PARENT_NAME = '{}'".format(absolute_path),
                               AS_LIST, ctx.callback):
        # Extract only the name of the sub-folder from the full name/path
        name = result[0].rsplit('/', 1)[1]
        relative_collection_path = result[0].replace(dropzone_path, "")
        folder_node = {
            "value": name,
            "id": relative_collection_path,
            "type": "folder",
            "size": 0,
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result[1])))
        }

        output.append(folder_node)

    for result in row_iterator("DATA_NAME, DATA_SIZE, DATA_CREATE_TIME",
                               "COLL_NAME = '{}'".format(absolute_path),
                               AS_LIST, ctx.callback):
        relative_data_path = absolute_path + "/" + result[0]
        relative_data_path = relative_data_path.replace(dropzone_path, "")
        data_node = {
            "value": result[0],
            "id": relative_data_path,
            "type": "file",
            "size": result[1],
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result[2])))
        }

        output.append(data_node)

    return output
