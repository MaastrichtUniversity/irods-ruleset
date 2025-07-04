from genquery import row_iterator, AS_LIST  # pylint: disable=import-error
from pathlib import Path


def dm_attr(ctx, unarchival_path, tape_resource, tape_resource_location):
    """
    Get the status of a file or collection on tape.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    unarchival_path: str
        The full path of the collection OR file to be unarchived, e.g. '/nlmumc/projects/P000000017/C000000001' or '/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log'
    tape_resource: str
        The name of the tape resource
    tape_resource_location: str
        The resource location listed for the tape resource (can be found with 'iadmin lr {}')

    Returns
    ----------
    dict
        A dictionary containing the files currently offline, unmigrating, online, and the total count
    """
    input_type = ctx.callback.msiGetObjType(unarchival_path, "")["arguments"][1]
    query = ""
    if input_type == "-c":
        query = "DATA_RESC_NAME = '{}' AND COLL_NAME LIKE '%{}%'".format(tape_resource, unarchival_path)
    elif input_type == "-d":
        file_name = Path(unarchival_path).name
        folder_name = unarchival_path.replace("/{}".format(file_name), "")
        query = "DATA_RESC_NAME = '{}' AND COLL_NAME = '{}' AND DATA_NAME = '{}'".format(
            tape_resource, folder_name, file_name
        )

    count = 0
    files = []
    for row in row_iterator("DATA_PATH,COLL_NAME,DATA_NAME", query, AS_LIST, ctx.callback):
        count += 1
        file_path = row[0]
        # The 'dmattr' call can also be called collection wide, but am choosing not to do so
        # because in the case of large amounts of files, the 'file_path' variable will be too
        # large for the iRODS server to handle, and will empty the variable and cause issues
        output = ctx.callback.dmattr(file_path, tape_resource_location, "")["arguments"][2].rstrip()
        file_status = output.split("+")[0]
        files.append(
            {"physical_path": file_path, "virtual_path": "{}/{}".format(row[1], row[2]), "status": file_status}
        )

    files_offline = [file for file in files if file["status"] == "OFL"]
    files_unmigrating = [file for file in files if file["status"] in ("QUE", "STG")]
    files_online = [file for file in files if file["status"] in ("DUL", "REG")]

    return {
        "files_offline": files_offline,
        "files_unmigrating": files_unmigrating,
        "files_online": files_online,
        "count": count,
    }
