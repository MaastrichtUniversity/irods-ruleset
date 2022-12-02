# /rules/tests/run_test.sh -r set_dropzone_total_size_avu -a "vast-dove,mounted"
import irods_types

from datahubirodsruleset.core import make, Output, format_dropzone_path


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def set_dropzone_total_size_avu(ctx, token, dropzone_type):
    """
    Set an attribute value with the total size of a dropzone

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token : str
        The token (i.e. 'vast-chinchilla')
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'

    Returns
    -------
    dict
        The attribute value
    """
    # Suppress [B404:blacklist] Consider possible security implications associated with subprocess module.
    # subprocess is only use for subprocess.check_output and its usage have been validated up to the following commit
    # hash: 02122d8f0c767fe79fbb8448db3fe8420cd36c14
    import subprocess  # nosec
    import re
    import datetime

    # we check drop zone token is valid
    # TODO: At the moment, this knowledge is distributed across multiple repositories,
    #       would be nice if it was just in one place. In case for example, we expand
    #       drop zone names to \w+-\w+.
    if re.search(r"^[a-z]+-[a-z]+$", token) is None:
        # -816000 CAT_INVALID_ARGUMENT
        ctx.callback.msiExit("-816000", "Invalid name for ingest zone")

    drop_zone_path = format_dropzone_path(ctx, token, dropzone_type)

    # This call makes sure that the dropzone path exists. If it does not exist,
    # iRODS will throw an exception and the rule execution will not continue
    try:
        ctx.callback.msiObjStat(drop_zone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    # Suppress [B603:subprocess_without_shell_equals_true] subprocess call - check for execution of untrusted input.
    # The input parameters of format_dropzone_path are validated inside the function before outputting drop_zone_path.
    # drop_zone_path is then again check against iRODS with msiObjStat.
    list_files = subprocess.check_output(["ils", "-lr", drop_zone_path], shell=False)  # nosec
    lines = list_files.splitlines()
    total_size = 0
    for line in lines:
        split_line = line.split()
        if len(split_line) > 4:
            try:
                # After the size is always a datetime in the output. If that isn't the case, this is a folder,
                # and it should not be calculated and parsed to an int (its subsequent files will)
                d = datetime.datetime.strptime(split_line[4], "%Y-%m-%d.%H:%M")
                total_size += int(split_line[3])
            except ValueError:
                continue
    kvp = ctx.callback.msiString2KeyValPair("{}={}".format("totalSize", total_size), irods_types.BytesBuf())[
        "arguments"
    ][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, drop_zone_path, "-C")
