# DONOTCALLDIRECTLY
import glob
import json
import os

from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING

PRE_INGEST_DOCUMENT_FOLDER = "/var/log/irods-pre-ingest"


@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def save_dropzone_pre_ingest_info(ctx, dropzone_path, depositor, dropzone_type, serialized_validation_errors):
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
        - Validation errors

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

    Returns
    -------
    list[str]
        The final validation errors, including errors found during the physical content scan.
    """
    token = dropzone_path.split("/")[-1]
    physical_path = ""
    if dropzone_type == "mounted":
        physical_path = os.path.join("/mnt/ingest/zones", token)
    elif dropzone_type == "direct":
        physical_path = os.path.join("/mnt/stagingResc01/ingest/direct/", token)

    validation_errors = json.loads(serialized_validation_errors)
    result = {"validation_errors": validation_errors}

    faulty_paths = []
    file_folder_structure = path_to_dict(physical_path, faulty_paths)
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

    is_ingestable = not faulty_paths
    ctx.callback.setCollectionAVU(dropzone_path, "isIngestable", formatters.format_boolean_to_string(is_ingestable))
    for faulty_path in faulty_paths:
        relative_path = os.path.relpath(faulty_path, physical_path)
        logical_path = dropzone_path
        if relative_path != ".":
            logical_path = f"{dropzone_path}/{relative_path.replace(os.sep, '/')}"
        validation_errors.append(f"Dropzone contains path with unsupported characters '{logical_path}'")

    # Keep document creation as the final side effect, after all validation errors are known.
    save_pre_ingest_document(ctx, result, token)
    return validation_errors


def path_to_dict(path, faulty_paths):
    """
    Recursive function to convert a folder to a dictionary containing all files and subdirectories (including files)

    Parameters
    ----------
    path: str
        Physical path to a directory
    faulty_paths: list[str]
        Physical paths containing an unsupported character combination

    Returns
    -------
    dict:
        All files and subdirectories of the input path
    """
    d = {"name": os.path.basename(path)}
    # Due to a bug in GenQuery https://github.com/irods/irods/issues/7302
    if "'" in path and " and " in path:
        faulty_paths.append(path)
    if os.path.isdir(path):
        d["type"] = "directory"
        d["children"] = [path_to_dict(os.path.join(path, x), faulty_paths) for x in os.listdir(path)]

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

    timestamp = time.time()

    creation_date = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    filename = f"{document['project']}_{token}_{creation_date}.json"

    document_path = f"{PRE_INGEST_DOCUMENT_FOLDER}/{filename}"
    ctx.callback.msiWriteRodsLog(f"DEBUG: Writing pre-ingest document {document_path}", 0)
    with open(document_path, "w", encoding="utf-8") as outfile:
        outfile.write(json.dumps(document, indent=4))
    return document_path


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def read_dropzone_validation_errors(ctx, project_id, token):
    """Read validation errors from the newest pre-ingest document for a dropzone."""
    filename_pattern = f"{glob.escape(project_id)}_{glob.escape(token)}_*.json"
    document_paths = glob.glob(os.path.join(PRE_INGEST_DOCUMENT_FOLDER, filename_pattern))
    if not document_paths:
        return {"found": False, "validation_errors": []}

    document_path = max(document_paths, key=lambda path: (os.path.getmtime(path), path))
    try:
        with open(document_path, encoding="utf-8") as infile:
            document = json.load(infile)
    except (OSError, ValueError) as error:
        raise RuntimeError(f"Failed reading pre-ingest document '{document_path}': {error}") from error

    if "validation_errors" not in document:
        return {"found": False, "validation_errors": []}

    validation_errors = document["validation_errors"]
    if not isinstance(validation_errors, list):
        raise RuntimeError(f"Invalid validation_errors in pre-ingest document '{document_path}'")

    return {"found": True, "validation_errors": validation_errors}
