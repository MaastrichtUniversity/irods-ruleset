@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def set_schema_avu_to_collection(ctx, project, collection):
    """
    Set collection AVU for the templateSchemaName and templateSchemaVersion based on the schema.json in the collection
        Parameters
     ----------
     ctx : Context
         Combined type of a callback and rei struct.
     project : str
         The project where the instance.json is to fill (ie. P000000010)
     collection : str
         The collection where the instance.json is to fill (ie. C000000002)
    """

    project_collection_full_path = "/nlmumc/projects/{}/{}".format(project, collection)
    # Setting the PID in the instance.json file
    instance_location = "{}/schema.json".format(project_collection_full_path)
    # Reading the schema.json and parsing it
    schema = read_data_object_from_irods(ctx, instance_location)
    schema_object = json.loads(schema)

    templateSchemaName = " "
    templateSchemaVersion = " "
    if "schema:name" in schema_object:
        templateSchemaName = schema_object["schema:name"]
    if "pav:version" in schema_object:
        templateSchemaVersion = schema_object["pav:version"]

    ctx.callback.setCollectionAVU(project_collection_full_path, "templateSchemaName", templateSchemaName)
    ctx.callback.setCollectionAVU(project_collection_full_path, "templateSchemaVersion", templateSchemaVersion)
