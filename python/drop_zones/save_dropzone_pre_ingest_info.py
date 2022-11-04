# /rules/tests/run_test.sh -r save_dropzone_pre_ingest_info -a "bla-token,C000000001,jmelius" -j
@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def save_dropzone_pre_ingest_info(ctx, token, collection_id, depositor):
    """
    This rule generates a json formatted string with information about provided mounted dropzone
    Included are:
        - file/folder structure names + individual file sizes
        - total number of files
        - total of individual file sizes
        - Dropzone type
        - Dropzone creator
        - Dropzone depositor
        - Collection id
        - Project id
        - Dropzone token

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The dropzone token, to locate the source collection; e.g: 'handsome-snake'
    collection_id: str
        The collection id, ie C00000004
    depositor: str
        The username of the person requesting the ingest

    returns
    -------
    str
        json formatted string with information about the dropzone content
    """
    import os
    import json

    dropzone_type = "mounted"

    dropzone_path = formatters.format_dropzone_path(token, dropzone_type)
    physical_path = os.path.join("/mnt/ingest/zones", token)

    result = {}

    file_folder_structure = path_to_dict(physical_path)
    result["file_folder_structure"] = file_folder_structure

    size = 0
    file_count = 0
    for item in gen_dict_extract("size", file_folder_structure):
        size = size + item
        file_count += 1

    result["total_file_size"] = size
    result["file_count"] = file_count
    result["depositor"] = depositor
    result["collection"] = collection_id
    result["type"] = dropzone_type

    result["creator"] = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
    result["project"] = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    result["title"] = ctx.callback.getCollectionAVU(dropzone_path, "title", "", "", TRUE_AS_STRING)["arguments"][2]

    save_pre_ingest_document(ctx, result, token)

    return json.dumps(result)


def path_to_dict(path):
    """
    Recursive function to convert a folder to a dictionary containing all files and subdirectories (including files)
    Parameters
    ----------
    path: str
        Physical path to a directory

    Returns
    -------
    dict:
        All files and subdirectories of the input path

    """
    import os

    d = {"name": os.path.basename(path)}
    if os.path.isdir(path):
        d["type"] = "directory"
        d["children"] = [path_to_dict(os.path.join(path, x)) for x in os.listdir(path)]
    else:
        d["type"] = "file"
        d["size"] = os.path.getsize(path)

    return d


def gen_dict_extract(key, var):
    if hasattr(var, "iteritems"):
        for k, v in var.iteritems():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result


def save_pre_ingest_document(ctx, document, token):
    """
    Write the pre-ingest json document to the pre-defined location.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    document: dict
        The dropzone information pre-ingest to save
    token: str
        The token, eg 'crazy-frog'
    """
    import time
    import datetime

    document_folder = "/var/log/irods-pre-ingest"
    timestamp = time.time()
    clean_up_pre_ingest_document(ctx, document_folder, timestamp)

    creation_date = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    filename = "{project_id}_{dropzone_token}_{date}.json".format(
        project_id=document["project"],
        dropzone_token=token,
        date=creation_date,
    )

    document_path = "{document_folder}/{filename}".format(document_folder=document_folder, filename=filename)
    with open(document_path, "w") as outfile:
        outfile.write(json.dumps(document, indent=4))
        ctx.callback.msiWriteRodsLog("DEBUG: Writing pre-ingest document {}".format(document_path), 0)


def clean_up_pre_ingest_document(ctx, document_folder, timestamp):
    """
    Remove all the old pre-ingest documents in the log folder that are older old 31 days than the input timestamp.

    Parameters
    ----------
    ctx
    document_folder: str
        The absolute path to the log folder
    timestamp: float
        The epoch timestamp. Usually execution time
    """
    import os

    one_month_in_seconds = 2678400  # 31 days

    # Get the absolute path of all json files present in the document_folder path
    documents = [os.path.join(document_folder, doc) for doc in os.listdir(document_folder) if doc.endswith(".json")]
    for document_filename in documents:
        ctime = os.path.getctime(document_filename)
        time_difference_in_seconds = int(timestamp) - int(ctime)
        if time_difference_in_seconds > one_month_in_seconds:
            ctx.callback.msiWriteRodsLog("DEBUG: Removing pre-ingest document {}".format(document_filename), 0)
            os.remove(document_filename)
