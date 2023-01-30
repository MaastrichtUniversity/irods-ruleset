# /rules/tests/run_test.sh -r create_ingest_metadata_snapshot -a "P000000010,C000000001,/nlmumc/ingest/zones/crazy-frog,false" -u jmelius -j
from subprocess import check_call, CalledProcessError

import irods_types  # pylint: disable=import-error
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs

from datahubirodsruleset import read_data_object_from_irods, TRUE_AS_STRING
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import (
    format_schema_versioned_collection_path,
    format_schema_collection_path,
    format_instance_collection_path,
    format_metadata_versions_path,
    format_instance_versioned_collection_path,
    format_project_path,
)


@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def create_ingest_metadata_snapshot(ctx, project_id, collection_id, source_collection, overwrite_flag):
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
                project_id, collection_id, source_collection, "Failed to create metadata ingest snapshot"
            )

    source_schema = format_schema_collection_path(ctx, project_id, collection_id)
    source_instance = format_instance_collection_path(ctx, project_id, collection_id)

    destination_schema = format_schema_versioned_collection_path(ctx, project_id, collection_id, "1")
    destination_instance = format_instance_versioned_collection_path(ctx, project_id, collection_id, "1")
    force_flag = ""
    if formatters.format_string_to_boolean(overwrite_flag):
        force_flag = "forceFlag="

    # Copy current metadata json files to /.metadata_versions
    try:
        icp_wrapper(ctx, source_schema, destination_schema, project_id)
        icp_wrapper(ctx, source_instance, destination_instance, project_id)
    except RuntimeError:
        ctx.callback.set_post_ingestion_error_avu(
            project_id, collection_id, source_collection, "Failed to create metadata ingest snapshot"
        )


def icp_wrapper(ctx, source, destination, project_id):
    destination_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]

    try:
        return_code = check_call(["icp", "-R", destination_resource, source, destination], shell=False)
    except CalledProcessError as err:
        ctx.callback.msiWriteRodsLog("ERROR: irsync: cmd '{}' retcode'{}'".format(err.cmd, err.returncode), 0)
        return_code = 1

    return return_code
