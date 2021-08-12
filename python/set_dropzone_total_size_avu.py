import subprocess
import re

@make(inputs=[0], outputs=[], handler=Output.STORE)
def set_dropzone_total_size_avu(ctx, token):
    """
    Set an attribute value with the total size of a dropzone

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    token : str
        The token (i.e. 'vast-chinchilla')

    Returns
    -------
    dict
        The attribute value
    """
    # we check drop zone token is valid
    # TODO: At the moment, this knowledge is distributed across multiple repositories,
    #       would be nice if it was just in one place. In case for example, we expand
    #       drop zone names to \w+-\w+.
    if re.search(r"^[a-z]+-[a-z]+$", token) is None:
        # -816000 CAT_INVALID_ARGUMENT
        ctx.callback.msiExit("-816000", "Invalid name for ingest zone")

    drop_zone_path = '/nlmumc/ingest/zones/{}'.format(token)

    # This call makes sure that the dropzone path exists. If it does not exist,
    # iRODS will throw an exception and the rule execution will not continue
    try:
        ctx.callback.msiObjStat(drop_zone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    list_files = subprocess.check_output(["ils", "-lr", drop_zone_path])
    lines = list_files.splitlines()
    total_size = 0
    for line in lines:
        split_line = line.split()
        if len(split_line) > 4:
            try:
                # After the size is always a datetime in the output. If that isnt the case, this is a folder
                # and it should not be calculated and parsed to an int (its subsequent files will)
                d = datetime.datetime.strptime(split_line[4], "%Y-%m-%d.%H:%M")
                total_size += int(split_line[3])
            except ValueError:
                continue
    kvp = ctx.callback.msiString2KeyValPair('{}={}'.format('totalSize', total_size), irods_types.BytesBuf())["arguments"][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, drop_zone_path, "-C")
