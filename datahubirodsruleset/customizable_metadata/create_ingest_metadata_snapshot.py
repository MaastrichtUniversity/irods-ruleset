# /rules/tests/run_test.sh -r create_ingest_metadata_snapshot -a "P000000010,C000000001,/nlmumc/ingest/zones/crazy-frog,false,jmelius" -u jmelius -j
import irods_types  # pylint: disable=import-error
from dhpythonirodsutils import formatters

from datahubirodsruleset import icp_wrapper
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import (
    format_schema_versioned_collection_path,
    format_schema_collection_path,
    format_instance_collection_path,
    format_metadata_versions_path,
    format_instance_versioned_collection_path,
)


@make(inputs=[0, 1, 2, 3, 4], outputs=[], handler=Output.STORE)
def create_ingest_metadata_snapshot(ctx, project_id, collection_id, source_collection, overwrite_flag, username):
    """
    Create a snapshot of the collection metadata files (schema & instance):
        * Check if the snapshot folder (.metadata_versions) already exists, if not create it
        * Copy the current metadata files to .metadata_versions and add a version 1 in the filename

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (e.g: P000000010)
    collection_id : str
        The collection where the instance.json is to fill (e.g: C000000002)
    source_collection: str
        The drop-zone absolute path (e.g: /nlmumc/ingest/zones/crazy-frog)
    overwrite_flag: str
        'true'/'false' expected; If true, the copy overwrites possible existing schema.1.json & instance.1.json files
    username: str
        The username of the person requesting the ingest
    """

    metadata_folder_path = format_metadata_versions_path(ctx, project_id, collection_id)
    metadata_folder_exist = True

    # Check .metadata_versions folder exists
    try:
        ctx.callback.msiObjStat(metadata_folder_path, irods_types.RodsObjStat())
    except RuntimeError:
        metadata_folder_exist = False

    if not metadata_folder_exist:
        try:
            ctx.callback.msiCollCreate(metadata_folder_path, 0, 0)
            ctx.callback.msiWriteRodsLog("DEBUG: '{}' created".format(metadata_folder_path), 0)
        except RuntimeError:
            ctx.callback.set_post_ingestion_error_avu(
                project_id, collection_id, source_collection, "Failed to create metadata ingest snapshot", username
            )

    source_schema = format_schema_collection_path(ctx, project_id, collection_id)
    source_instance = format_instance_collection_path(ctx, project_id, collection_id)

    destination_schema = format_schema_versioned_collection_path(ctx, project_id, collection_id, "1")
    destination_instance = format_instance_versioned_collection_path(ctx, project_id, collection_id, "1")
    force_flag = formatters.format_string_to_boolean(overwrite_flag)

    # Copy current metadata json files to /.metadata_versions
    try:
        icp_wrapper(ctx, source_schema, destination_schema, project_id, force_flag)
        icp_wrapper(ctx, source_instance, destination_instance, project_id, force_flag)
    except RuntimeError:
        ctx.callback.set_post_ingestion_error_avu(
            project_id, collection_id, source_collection, "Failed to create metadata ingest snapshot", username
        )
