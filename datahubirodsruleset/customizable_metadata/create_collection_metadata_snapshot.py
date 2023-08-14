# /rules/tests/run_test.sh -r create_collection_metadata_snapshot -a "P000000014,C000000001" -u jmelius -j
import json

import irods_types  # pylint: disable=import-error
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import (
    format_project_collection_path,
    format_schema_collection_path,
    format_instance_collection_path,
    format_metadata_versions_path,
    format_schema_versioned_collection_path,
    format_instance_versioned_collection_path,
    format_project_path,
)
from datahubirodsruleset.utils import FALSE_AS_STRING, icp_wrapper


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def create_collection_metadata_snapshot(ctx, project_id, collection_id):
    """
    Create a snapshot of the collection metadata files (schema & instance):
        * Check user edit metadata permission
        * Check if the snapshot folder (.metadata_versions) already exists, if not create it
        * Request the new versions handle PIDs
        * Update instance.json and schema.json properties
        * Copy the current metadata files to .metadata_versions and add the version number in the filename
        * Update the metadata in the elastic index
        * Increment the AVU latest_version_number

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project where the instance.json is to fill (e.g: P000000010)
    collection_id : str
        The collection where the instance.json is to fill (e.g: C000000002)

    Returns
    -------
    bool
        PIDs request status; If true, the handle PIDs were successfully requested.
    """
    project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
    project_path = format_project_path(ctx, project_id)
    metadata_folder_path = format_metadata_versions_path(ctx, project_id, collection_id)
    metadata_folder_exist = True
    pid_request_status = True

    # Check if user is allowed to edit metadata for this project
    can_edit_metadata = ctx.callback.check_edit_metadata_permission(project_path, "")["arguments"][1]
    if not formatters.format_string_to_boolean(can_edit_metadata):
        ctx.callback.msiExit("-1", "ERROR: User has no edit metadata rights for  '{}'".format(project_id))

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
            ctx.callback.msiExit("-1", "ERROR: Couldn't create '{}'".format(metadata_folder_path))

    source_schema = format_schema_collection_path(ctx, project_id, collection_id)
    source_instance = format_instance_collection_path(ctx, project_id, collection_id)

    version = ctx.callback.getCollectionAVU(project_collection_path, "latest_version_number", "", "", FALSE_AS_STRING)[
        "arguments"
    ][2]
    new_version = 0
    try:
        version_number = int(version)
        new_version = version_number + 1
    except ValueError:
        ctx.callback.msiExit(
            "-1",
            "ERROR: 'Cannot increment version number '{}' for collection '{}'".format(version, project_collection_path),
        )

    destination_schema = format_schema_versioned_collection_path(ctx, project_id, collection_id, new_version)
    destination_instance = format_instance_versioned_collection_path(ctx, project_id, collection_id, new_version)

    # Request new PIDs
    handle_pids_version = ctx.callback.get_versioned_pids(project_id, collection_id, str(new_version), "")["arguments"][
        3
    ]
    handle_pids_version = json.loads(handle_pids_version)
    if (
        not handle_pids_version
        or "collection" not in handle_pids_version
        or handle_pids_version["collection"]["handle"] == ""
    ):
        pid_request_status = False

    try:
        ctx.callback.update_metadata_during_edit_collection(project_id, collection_id, str(new_version))
    except RuntimeError:
        ctx.callback.msiExit("-1", "ERROR: Couldn't update the instance snapshot '{}'".format(destination_instance))

    # Copy current metadata json files to /.metadata_versions
    try:
        icp_wrapper(ctx, source_schema, destination_schema, project_id, False)
        icp_wrapper(ctx, source_instance, destination_instance, project_id, False)
    except RuntimeError:
        ctx.callback.msiExit("-1", "ERROR: Couldn't create the metadata snapshots '{}'".format(metadata_folder_path))

    # Only set latest_version_number if everything went fine.
    ctx.callback.setCollectionAVU(project_collection_path, "latest_version_number", str(new_version))

    # Update the metadata in the elastic index
    ctx.callback.index_update_single_project_collection_metadata(project_id, collection_id, "", "")

    return pid_request_status
