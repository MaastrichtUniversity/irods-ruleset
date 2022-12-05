# /rules/tests/run_test.sh -r get_project_collection_tape_estimate -a "P000000014,C000000001" -j
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path, format_project_collection_path
from datahubirodsruleset.utils import FALSE_AS_STRING


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_collection_tape_estimate(ctx, project_id, collection_id):
    """
    The project collection tape status & the number and total bytes size of files eligible for tape

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project's id; e.g: P000000010
    collection_id: str
        The collection's id; e.g: C000000001

    Returns
    -------
    dict
        The project_id collection tape status, above_threshold and archivable
    """
    project_path = format_project_path(ctx, project_id)
    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    # Get the destination archive resource from the project
    ret = ctx.getCollectionAVU(
        project_path, ProjectAVUs.ARCHIVE_DESTINATION_RESOURCE.value, "archive_resource", "", FALSE_AS_STRING
    )
    archive_resource = ret["arguments"][2]

    minimum_size = 262144000  # The minimum file size (in bytes)

    number_files = 0
    bytes_size = 0
    condition = "COLL_NAME = '{}' || like '{}/%' AND DATA_SIZE  >= '{}'".format(
        project_collection_path, project_collection_path, minimum_size
    )
    for data in row_iterator("DATA_NAME, DATA_SIZE", condition, AS_LIST, ctx.callback):
        number_files += 1
        bytes_size += int(data[1])

    above_threshold = {"number_files": number_files, "bytes_size": bytes_size}

    number_files = 0
    bytes_size = 0
    for data in row_iterator(
        "DATA_NAME, DATA_SIZE",
        "COLL_NAME = '{}' || like '{}/%' ".format(project_collection_path, project_collection_path)
        + " AND DATA_RESC_NAME != '{}' ".format(archive_resource)
        + " AND DATA_SIZE >= '{}'".format(minimum_size),
        AS_LIST,
        ctx.callback,
    ):
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
