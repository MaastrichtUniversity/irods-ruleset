import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import read_data_object_from_irods


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def validate_metadata(ctx, source_collection):
    """
    Validate the metadata that is about to be ingested

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    source_collection: str
        The collection to validate the metadata from (e.g: /nlmumc/ingest/zones/bla-token)

    Returns
    -------
    bool
        True if valid, False if not
    """
    import jsonschema

    try:
        instance = read_data_object_from_irods(ctx, f"{source_collection}/instance.json")
        schema = read_data_object_from_irods(ctx, f"{source_collection}/schema.json")
    except RuntimeError:
        ctx.callback.msiWriteRodsLog(f"Empty/Missing json files '{source_collection}'", 0)
        return False

    try:
        instance_object = json.loads(instance)
    except ValueError:
        ctx.callback.msiWriteRodsLog(
            f"JSONschema validation failed to parse instance.json for '{source_collection}'", 0
        )
        return False

    try:
        schema_object = json.loads(schema)
    except ValueError:
        ctx.callback.msiWriteRodsLog(
            f"JSONschema validation failed to parse schema.json for '{source_collection}'", 0
        )
        return False

    try:
        # The actual validation occurs here. This can throw two types of exceptions, which we catch below
        jsonschema.validate(instance_object, schema_object)
        return True
    except jsonschema.exceptions.ValidationError:
        ctx.callback.msiWriteRodsLog(f"JSONschema validation error occurred for '{source_collection}'", 0)
    except jsonschema.exceptions.SchemaError:
        ctx.callback.msiWriteRodsLog(f"JSONschema schema error occurred for '{source_collection}'", 0)

    return False
