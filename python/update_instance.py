@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def update_instance(ctx, project, collection, handle):
    """
    Fill an already ingested 'instance.json' file located on the root
    of a collection with
    - A handle PID as 'identifier'
    - A submission date

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project : str
        The project where the instance.json is to fill (ie. P000000010)
    collection : str
        The collection where the instance.json is to fill (ie. C000000002)
    handle : str
        The handle to insert into the instance.json (ie. 21.T12996/P000000001C000000195)
    """
    import datetime

    project_collection_full_path = "/nlmumc/projects/{}/{}".format(project, collection)

    # Setting the PID in the instance.json file
    instance_location = "{}/instance.json".format(project_collection_full_path)
    # Reading the instance.json and parsing it
    instance = read_data_object_from_irods(ctx, instance_location)
    instance_object = json.loads(instance)

    # Overwriting the current values for identifier
    if handle:
        handle_url = "https://hdl.handle.net/" + handle
        instance_object["1_Identifier"]["datasetIdentifier"]["@value"] = handle_url
        instance_object["@id"] = handle_url

    # Set identifier type to "handle"
    instance_object["1_Identifier"]["datasetIdentifierType"]["rdfs:label"] = "Handle"
    instance_object["1_Identifier"]["datasetIdentifierType"]["@id"] = "http://vocab.fairdatacollective.org/gdmt/Handle"

    # Overwriting the current value for submission date
    instance_object["8_Date"]["datasetDate"]["@value"] = datetime.datetime.now().strftime("%Y-%m-%d")
    instance_object["8_Date"]["datasetDateType"]["rdfs:label"] = "Submitted"
    instance_object["8_Date"]["datasetDateType"]["@id"] = "http://vocab.fairdatacollective.org/gdmt/Submitted"

    # Overwriting the schema:isBasedOn with the MDR schema handle URL
    mdr_handle_url = ctx.callback.msi_getenv("MDR_HANDLE_URL", "")["arguments"][1]
    schema_url = "{}{}/{}/schema".format(mdr_handle_url, project, collection)
    instance_object["schema:isBasedOn"] = schema_url

    # Opening the instance file with read/write access
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + instance_location + "++++openFlags=O_RDWR", 0)
    opened_file = ret_val["arguments"][1]
    ctx.callback.msiDataObjWrite(opened_file, json.dumps(instance_object, indent=4), 0)
    ctx.callback.msiDataObjClose(opened_file, 0)
