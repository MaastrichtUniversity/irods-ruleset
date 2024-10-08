# /rules/tests/run_test.sh -r update_metadata_during_ingest -a "P000000014,C000000001,21.T12996/P000000001C000000195,2" -u jmelius
import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_instance_collection_path, format_schema_collection_path
from datahubirodsruleset.utils import read_data_object_from_irods, iput_wrapper


@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def update_metadata_during_ingest(ctx, project_id, collection_id, handle, version):
    """
    Fill an already ingested 'instance.json' and 'schema.json' file located on the root
    of a collection with
    - A handle PID as 'identifier'
    - A submission date
    - @id for schema to PID

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (e.g: P000000010)
    collection_id : str
        The collection where the instance.json is to fill (e.g: C000000002)
    handle : str
        The handle to insert into the instance.json (e.g: 21.T12996/P000000001C000000195)
    version: str
        The version of the identifiers to use in instance.json and schema.json
    """
    import datetime
    import tempfile

    # Setting the PID in the instance.json file
    instance_location = format_instance_collection_path(ctx, project_id, collection_id)
    # Reading the instance.json and parsing it
    instance = read_data_object_from_irods(ctx, instance_location)
    instance_object = json.loads(instance)

    # Overwriting the current values for identifier
    if handle:
        handle_url = "https://hdl.handle.net/" + handle
        instance_object["1_Identifier"]["datasetIdentifier"]["@value"] = handle_url + "." + version
        instance_object["@id"] = handle_url + "instance." + version

    # Set identifier type to "handle"
    instance_object["1_Identifier"]["datasetIdentifierType"]["rdfs:label"] = "Handle"
    instance_object["1_Identifier"]["datasetIdentifierType"]["@id"] = "http://vocab.fairdatacollective.org/gdmt/Handle"

    # Overwriting the current value for submission date
    instance_object["8_Date"]["datasetDate"]["@value"] = datetime.datetime.now().strftime("%Y-%m-%d")
    instance_object["8_Date"]["datasetDateType"]["rdfs:label"] = "Submitted"
    instance_object["8_Date"]["datasetDateType"]["@id"] = "http://vocab.fairdatacollective.org/gdmt/Submitted"

    # Overwriting the schema:isBasedOn with the PID for schema version
    schema_url = "https://hdl.handle.net/{}{}.{}".format(handle, "schema", version)
    instance_object["schema:isBasedOn"] = schema_url

    tmp_instance = tempfile.NamedTemporaryFile(delete=True, mode = "w")
    try:
        tmp_instance.write(json.dumps(instance_object, indent=4))
        ctx.callback.msiWriteRodsLog(f"DEBUG: Writing modified instance to local file '{tmp_instance.name}'", 0)
        iput_wrapper(ctx, tmp_instance.name, instance_location, project_id, True)
        ctx.callback.msiWriteRodsLog(f"DEBUG: Successfully overwrote {instance_location}'", 0)
    finally:
        tmp_instance.close()

    # Setting the PID in the schema.json file
    schema_location = format_schema_collection_path(ctx, project_id, collection_id)
    # Reading the instance.json and parsing it
    schema = read_data_object_from_irods(ctx, schema_location)
    schema_object = json.loads(schema)
    schema_object["@id"] = schema_url

    tmp_schema = tempfile.NamedTemporaryFile(delete=True, mode = "w")
    try:
        tmp_schema.write(json.dumps(schema_object, indent=4))
        ctx.callback.msiWriteRodsLog(f"DEBUG: Writing modified schema to local file '{tmp_schema.name}'", 0)
        iput_wrapper(ctx, tmp_schema.name, schema_location, project_id, True)
        ctx.callback.msiWriteRodsLog(f"DEBUG: Successfully overwrote {schema_location}'", 0)
    finally:
        tmp_instance.close()
