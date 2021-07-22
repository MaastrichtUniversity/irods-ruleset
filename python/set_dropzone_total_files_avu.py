import subprocess

@make(inputs=[0], outputs=[], handler=Output.STORE)
def set_dropzone_total_files_avu(ctx, token):
    """
    Set an attribute value with the total number of files in a dropzone

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
    list_files = subprocess.check_output(["ils", "-lr", drop_zone_path])
    num_files = list_files.split().count('rods')
    kvp = ctx.callback.msiString2KeyValPair('{}={}'.format('numFiles', num_files), irods_types.BytesBuf())["arguments"][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, drop_zone_path, "-C")
