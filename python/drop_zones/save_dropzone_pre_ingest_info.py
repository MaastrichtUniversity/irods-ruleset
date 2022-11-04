# /rules/tests/run_test.sh -r save_dropzone_pre_ingest_info -a "bla-token" -j
@make(inputs=[0], outputs=[1], handler=Output.STORE)
def save_dropzone_pre_ingest_info(ctx, token):
    import os
    import json

    result = {}

    dropzone_path = formatters.format_dropzone_path(token, "mounted")
    physical_path = os.path.join("/mnt/ingest/zones", token)

    file_folder_structure = path_to_dict(physical_path)
    result['file_folder_structure'] = file_folder_structure

    size = 0
    file_count = 0
    for item in gen_dict_extract("size", file_folder_structure):
        size = size + item
        file_count += 1

    type_count = 0
    for item in gen_dict_extract("type", file_folder_structure):
        type_count += 1

    result['dir_count'] = type_count - file_count
    result['total_file_size'] = size
    result['file_count'] = file_count
    result['user_running_the_ingest'] = ctx.callback.get_client_username("")["arguments"][0]

    result['creator'] = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]
    result['project'] = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    result['title'] = ctx.callback.getCollectionAVU(dropzone_path, "title", "", "", TRUE_AS_STRING)["arguments"][2]

    save_pre_ingest_document(ctx, result, token)

    return json.dumps(result)


def path_to_dict(path):
    import os

    d = {'name': os.path.basename(path)}
    if os.path.isdir(path):
        d['type'] = "directory"
        d['children'] = [path_to_dict(os.path.join(path, x)) for x in os.listdir(path)]
    else:
        d['type'] = "file"
        d['size'] = os.path.getsize(path)

    return d


def gen_dict_extract(key, var):
    if hasattr(var, 'iteritems'):  # hasattr(var,'items') for python 3
        for k, v in var.iteritems():  # var.items() for python 3
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

