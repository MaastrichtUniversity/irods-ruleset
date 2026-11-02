# /rules/tests/run_test.sh -r update_metadata_during_edit_collection -a "P000000014,C000000001,2" -u jmelius
import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_instance_collection_path, format_schema_collection_path
from datahubirodsruleset.utils import read_data_object_from_irods


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def update_metadata_during_edit_collection(ctx, project_id, collection_id, version):
    """
    Update an already ingested 'instance.json' and 'schema.json' files on the project collection root level.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (e.g: P000000010)
    collection_id : str
        The collection where the instance.json is to fill (e.g: C000000002)
    version: str
        The version that should be used to create the handles (e.g: 3)
    """

    instance = json.loads(
        read_data_object_from_irods(ctx, format_instance_collection_path(ctx, project_id, collection_id))
    )
    schema = json.loads(
        read_data_object_from_irods(ctx, format_schema_collection_path(ctx, project_id, collection_id))
    )
    write_versioned_metadata(ctx, project_id, collection_id, version, instance, schema)


def write_versioned_metadata(ctx, project_id, collection_id, version, instance_object, schema_object):
    """Finalize identifiers before writing each document once."""
    # DHDO-2369: Apply identifiers in memory so staged saves need only one write
    # per final document; legacy snapshot callers reuse the same identifier logic.
    # Getting the epicpid url and prefix
    epicpid_base = ctx.callback.get_env("EPICPID_URL", "true", "")["arguments"][2]
    epicpid_prefix = epicpid_base.rsplit("/", 2)[1]

    # Set up all the handles
    schema_handle = f"https://hdl.handle.net/{epicpid_prefix}/{project_id}{collection_id}schema.{version}"
    instance_handle = f"https://hdl.handle.net/{epicpid_prefix}/{project_id}{collection_id}instance.{version}"
    project_collection_handle = f"https://hdl.handle.net/{epicpid_prefix}/{project_id}{collection_id}.{version}"

    # Set instance schema:isBasedOn to the schema version PID
    instance_object["schema:isBasedOn"] = schema_handle

    # Set element 1_Identifier values
    instance_object["1_Identifier"]["datasetIdentifier"]["@value"] = project_collection_handle
    instance_object["1_Identifier"]["datasetIdentifierType"]["rdfs:label"] = "Handle"
    instance_object["1_Identifier"]["datasetIdentifierType"]["@id"] = "http://vocab.fairdatacollective.org/gdmt/Handle"

    # Set instance @id to the instance version PID
    instance_object["@id"] = instance_handle

    # Setting the PID in the schema.json file
    schema_object["@id"] = schema_handle

    for path, document in (
        (format_instance_collection_path(ctx, project_id, collection_id), instance_object),
        (format_schema_collection_path(ctx, project_id, collection_id), schema_object),
    ):
        ret_val = ctx.callback.msiDataObjOpen("objPath=" + path + "++++openFlags=O_WRONLYO_TRUNC", 0)
        descriptor = ret_val["arguments"][1]
        try:
            ctx.callback.msiDataObjWrite(descriptor, json.dumps(document, indent=4), 0)
        finally:
            ctx.callback.msiDataObjClose(descriptor, 0)
