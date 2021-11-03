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
        true if valid, false if not
    """
    instance = read_data_object_from_irods(ctx, "/nlmumc/ingest/zones/{}/instance.json".format(token))
    schema = read_data_object_from_irods(ctx, "/nlmumc/ingest/zones/{}/schema.json".format(token))

    return schema
