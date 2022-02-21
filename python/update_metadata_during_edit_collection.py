@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def update_metadata_during_edit_collection(ctx, project_id, collection_id, version):
    """
    Update an already ingested 'instance.json' and 'schema.json' files on the project collection root level.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (ie. P000000010)
    collection_id : str
        The collection where the instance.json is to fill (ie. C000000002)
    version: str
        The version that should be used to create the handles (ie. 3)
    """

    # Getting the epicpid url and prefix
    epicpid_base = ctx.callback.msi_getenv("EPICPID_URL", "")["arguments"][1]
    epicpid_prefix = epicpid_base.rsplit("/", 2)[1]

    # Set up project collection path
    project_collection_full_path = "/nlmumc/projects/{}/{}".format(project_id, collection_id)

    # Set up all the handles
    schema_handle = "https://hdl.handle.net/{}/{}{}{}.{}".format(epicpid_prefix, project_id, collection_id, "schema", version)
    instance_handle = "https://hdl.handle.net/{}/{}{}{}.{}".format(epicpid_prefix, project_id, collection_id, "instance", version)
    project_collection_handle = "https://hdl.handle.net/{}/{}{}.{}".format(epicpid_prefix, project_id, collection_id, version)

    # Reading the instance.json and parsing it
    instance_location = "{}/instance.json".format(project_collection_full_path)
    instance = read_data_object_from_irods(ctx, instance_location)
    instance_object = json.loads(instance)

    # Set instance schema:isBasedOn to the schema version PID
    instance_object["schema:isBasedOn"] = schema_handle

    # Set element 1_Identifier values
    instance_object["1_Identifier"]["datasetIdentifier"]["@value"] = project_collection_handle
    instance_object["1_Identifier"]["datasetIdentifierType"]["rdfs:label"] = "Handle"
    instance_object["1_Identifier"]["datasetIdentifierType"]["@id"] = "http://vocab.fairdatacollective.org/gdmt/Handle"

    # Set instance @id to the instance version PID
    instance_object["@id"] = instance_handle

    # Opening the instance file with read/write access
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + instance_location + "++++openFlags=O_RDWR", 0)
    opened_file = ret_val["arguments"][1]
    ctx.callback.msiDataObjWrite(opened_file, json.dumps(instance_object, indent=4), 0)
    ctx.callback.msiDataObjClose(opened_file, 0)

    # Setting the PID in the schema.json file
    schema_location = "{}/schema.json".format(project_collection_full_path)
    # Reading the instance.json and parsing it
    schema = read_data_object_from_irods(ctx, schema_location)
    schema_object = json.loads(schema)
    schema_object["@id"] = schema_handle

    # Opening the schema file with read/write access
    ret_val = ctx.callback.msiDataObjOpen("objPath=" + schema_location + "++++openFlags=O_RDWR", 0)
    opened_schema_file = ret_val["arguments"][1]
    ctx.callback.msiDataObjWrite(opened_schema_file, json.dumps(schema_object, indent=4), 0)
    ctx.callback.msiDataObjClose(opened_schema_file, 0)
