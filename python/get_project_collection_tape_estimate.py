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

    above_threshold_number_files = 0
    above_threshold_bytes_size = 0
    archivable_number_files = 0
    archivable_bytes_size = 0

    condition = "COLL_NAME like '{}%' AND DATA_SIZE  >= '{}'".format(collection_path, minimum_size)
    for data in row_iterator("COUNT(DATA_PATH), SUM(DATA_SIZE), RESC_NAME", condition, AS_LIST, ctx.callback):
        count_number_files = int(data[0])
        sum_data_size = int(data[1])
        resource_name = data[2]
        if resource_name != archive_resource and "-repl" not in resource_name:
            archivable_number_files += count_number_files
            archivable_bytes_size += sum_data_size
            above_threshold_number_files += count_number_files
            above_threshold_bytes_size += sum_data_size
        elif resource_name == archive_resource and "-repl" not in resource_name:
            above_threshold_number_files += count_number_files
            above_threshold_bytes_size += sum_data_size

    above_threshold = {"number_files": above_threshold_number_files, "bytes_size": above_threshold_bytes_size}
    archivable = {"number_files": archivable_number_files, "bytes_size": archivable_bytes_size}

    status = ""
    if above_threshold["number_files"] == archivable["number_files"]:
        status = "online"
    if above_threshold["number_files"] != archivable["number_files"]:
        status = "mixed"
    if archivable["number_files"] == 0 and above_threshold["number_files"] > 0:
        status = "offline"

    output = {"above_threshold": above_threshold, "archivable": archivable, "status": status}

    return output
