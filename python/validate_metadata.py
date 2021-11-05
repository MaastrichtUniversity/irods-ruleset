import jsonschema

@make(inputs=[0], outputs=[1], handler=Output.STORE)
def validate_metadata(ctx, token):
    """
    Validate the metadata that is about to be ingested

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    token: str
        The token of the dropzone to validate the metadata from

    Returns
    -------
    bool
        True if valid, False if not
    """
    instance = read_data_object_from_irods(ctx, "/nlmumc/ingest/zones/{}/instance.json".format(token))
    schema = read_data_object_from_irods(ctx, "/nlmumc/ingest/zones/{}/schema.json".format(token))

    is_valid = False
    try:
        instance_object = json.loads(instance)
    except ValueError:
        ctx.callback.msiWriteRodsLog("JSONschema validation failed to parse instance.json for '{}'".format(token), 0)

    try:
        schema_object = json.loads(schema)
    except ValueError:
        ctx.callback.msiWriteRodsLog("JSONschema validation failed to parse schema.json for '{}'".format(token), 0)

    try:
        # The actual validation occurs here. This can throw two types of exceptions, which we catch below
        jsonschema.validate(instance_object, schema_object)
        is_valid = True
    except jsonschema.exceptions.ValidationError:
        ctx.callback.msiWriteRodsLog("JSONschema validation error occurred for '{}'".format(token), 0)
    except jsonschema.exceptions.SchemaError:
        ctx.callback.msiWriteRodsLog("JSONschema schema error occurred for '{}'".format(token), 0)

    return is_valid
