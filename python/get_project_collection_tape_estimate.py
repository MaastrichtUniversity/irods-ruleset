@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_collection_tape_estimate(ctx, project, collection):
    """
    The project collection tape status & the number and total bytes size of files eligible for tape

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project: str
        The project's id; e.g P000000010
    collection: str
        The collection's id; e.g C000000001

    Returns
    -------
    dict
        The project collection tape status, above_threshold and archivable
    """
    project_path = "/nlmumc/projects/{}".format(project)
    collection_path = "/nlmumc/projects/{}/{}".format(project, collection)
    # Get the destination archive resource from the project
    ret = ctx.getCollectionAVU(project_path, "archiveDestinationResource", "archive_resource", "", "false")
    archive_resource = ret["arguments"][2]

    minimum_size = 262144000  # The minimum file size (in bytes)

    number_files = 0
    bytes_size = 0
    condition = "COLL_NAME = '{}' || like '{}/%' AND DATA_SIZE  >= '{}'".format(collection_path, collection_path,
                                                                                minimum_size)
    for data in row_iterator("DATA_NAME, DATA_SIZE", condition, AS_LIST, ctx.callback):
        number_files += 1
        bytes_size += int(data[1])

    above_threshold = {"number_files": number_files, "bytes_size": bytes_size}

    number_files = 0
    bytes_size = 0
    for data in row_iterator("DATA_NAME, DATA_SIZE",
                             "COLL_NAME = '{}' || like '{}/%' ".format(collection_path, collection_path) +
                             " AND DATA_RESC_NAME != '{}' ".format(archive_resource) +
                             " AND DATA_SIZE >= '{}'".format(minimum_size),
                             AS_LIST,
                             ctx.callback):
        number_files += 1
        bytes_size += int(data[1])

    archivable = {"number_files": number_files, "bytes_size": bytes_size}

    status = ""
    if above_threshold["number_files"] == archivable["number_files"]:
        status = "online"
    if above_threshold["number_files"] != archivable["number_files"]:
        status = "mixed"
    if archivable["number_files"] == 0 and above_threshold["number_files"] > 0:
        status = "offline"

    output = {"above_threshold": above_threshold, "archivable": archivable, "status": status}

    return output
