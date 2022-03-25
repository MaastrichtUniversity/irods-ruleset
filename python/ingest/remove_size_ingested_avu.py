@make(inputs=[0], outputs=[], handler=Output.STORE)
def remove_size_ingested_avu(ctx, path):
    """
    Set the ACL of a given collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    path : str
        The absolute path of the collection
    """
    attribute = "sizeIngested"
    output = ctx.get_collection_attribute_value(path, attribute, "result")["arguments"][2]
    value = json.loads(output)["value"]

    if value != "":
        kvp = ctx.callback.msiString2KeyValPair("{}={}".format(attribute, value), irods_types.BytesBuf())["arguments"][
            1
        ]
        ctx.callback.msiRemoveKeyValuePairsFromObj(kvp, path, "-C")
        ctx.callback.msiWriteRodsLog("INFO: {}: Remove AVU '{}':'{}'".format(path, attribute, value), 0)
