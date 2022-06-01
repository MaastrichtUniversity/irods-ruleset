# /rules/tests/run_test.sh -r get_dropzone_folders -a "vast-dove"
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_dropzone_folders(ctx, token):
    """
    Lists the folders and files attributes at the input 'path'

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token : str
       The dropzone token

    Returns
    -------
    dict
       The folders and files attributes at the requested path
    """

    import time

    output = {"folders": []}

    absolute_path = "/nlmumc/ingest/direct/{}".format(token)

    # Get sub-folders
    for result in row_iterator("COLL_NAME, COLL_CREATE_TIME, COLL_MODIFY_TIME", "COLL_PARENT_NAME LIKE '{}'".format(absolute_path), AS_LIST, ctx.callback):

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
