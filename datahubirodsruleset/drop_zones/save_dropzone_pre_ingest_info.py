# /rules/tests/run_test.sh -r save_dropzone_pre_ingest_info -a "bla-token,jmelius,mounted" -j
import json

from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING

dropzone_is_ingestable = {"dropzone_is_ingestable": True}

@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def save_dropzone_pre_ingest_info(ctx, dropzone_path, depositor, dropzone_type):
    """
    This rule generates a json formatted string with information about the provided dropzone
    Included are:
        - File/folder structure names + individual file sizes
        - Total number of files
        - Total of individual file sizes
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
    dropzone_path: str
        path to the dropzone (e.g: /nlmumc/ingest/zones/crazy-frog
    depositor: str
        The username of the person requesting to ingest
    dropzone_type: str
        The type of dropzone
    """
    import os

    token = dropzone_path.split("/")[-1]
    physical_path = ""
    if dropzone_type == "mounted":
        physical_path = os.path.join("/mnt/ingest/zones", token)
    elif dropzone_type == "direct":
        physical_path = os.path.join("/mnt/stagingResc01/ingest/direct/", token)

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
    result["type"] = dropzone_type
    result["token"] = token
    result["creator"] = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
    result["project"] = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    result["title"] = ctx.callback.getCollectionAVU(dropzone_path, "title", "", "", TRUE_AS_STRING)["arguments"][2]
    ctx.callback.setCollectionAVU(dropzone_path, "totalSize", str(size))
    ctx.callback.setCollectionAVU(dropzone_path, "numFiles", str(file_count))

    is_ingestable = dropzone_is_ingestable["dropzone_is_ingestable"]
    ctx.callback.setCollectionAVU(dropzone_path, "isIngestable", formatters.format_boolean_to_string(is_ingestable))

    save_pre_ingest_document(ctx, result, token)


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
    # Due to a bug in GenQuery https://github.com/irods/irods/issues/7302
    if "'" in path and " and " in path:
        dropzone_is_ingestable["dropzone_is_ingestable"] = False
    if os.path.isdir(path):
        d["type"] = "directory"
        d["children"] = [path_to_dict(os.path.join(path, x)) for x in os.listdir(path)]

    else:
        d["type"] = "file"
        d["size"] = os.path.getsize(path)

    return d


def gen_dict_extract(key, var):
    """
    Find all occurrences of a key in nested dictionaries and lists
    Source:
    https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-dictionaries-and-lists

    Parameters
    ----------
    key: str
        key for which the value  will be returned
    var: dict
        (Nested) dict that can contain lists

    Returns
    -------
    Iterator[str]
        List generator that return the values for the key given that occur in the input dict
    """
    if hasattr(var, "items"):
        for k, v in var.items():
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
    return document_path