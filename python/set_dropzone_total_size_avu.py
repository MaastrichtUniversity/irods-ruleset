import subprocess

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
    drop_zone_path = '/nlmumc/ingest/zones/{}'.format(token)

    # This call makes sure that the dropzone path exists. If it does not exist,
    # iRODS will throw an exception and the rule execution will not continue
    try:
        ctx.callback.msiObjStat(drop_zone_path, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")

    list_files = subprocess.check_output(["ils", "-lr", drop_zone_path])
    lines = list_files.splitlines()[1:]
    total_size = 0
    for line in lines:
        total_size += int(line.split()[3])
    kvp = ctx.callback.msiString2KeyValPair('{}={}'.format('totalSize', total_size), irods_types.BytesBuf())["arguments"][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, drop_zone_path, "-C")
