@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def update_instance_snapshot(ctx, instance_location, schema_url, handle):
    """
    Update an already ingested 'instance_{timestamp}.json' file located in .metadata_versions

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    instance_location : str
        The absolute path of the instance; e.g: /nlmumc/projects/P000000014/C000000001/.metadata_versions/instance_2021-11-29_10-13-03-101799.json
    schema_url : str
        The schema URL to value to replace in the instance; e.g: http://mdr.local.dh.unimaas.nl/hdl/P000000014/C000000001/schema_2021-11-29_10-49-09-885586/
    handle: str
        The (versioned) handle PID for the collection
    """
    # Reading the instance.json and parsing it
    instance = read_data_object_from_irods(ctx, instance_location)
    instance_object = json.loads(instance)

    instance_object["schema:isBasedOn"] = schema_url

    new_handle = "https://hdl.handle.net/" + handle
    instance_object["1_Identifier"]["datasetIdentifier"]["@value"] = new_handle
    instance_object["@id"] = new_handle

    # Opening the instance file with read/write access
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + instance_location + "++++openFlags=O_RDWR", 0)
    opened_file = ret_val["arguments"][1]
    ctx.callback.msiDataObjWrite(opened_file, json.dumps(instance_object, indent=4), 0)
    ctx.callback.msiDataObjClose(opened_file, 0)
