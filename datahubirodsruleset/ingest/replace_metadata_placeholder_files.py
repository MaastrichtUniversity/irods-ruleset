# /rules/tests/run_test.sh -r replace_metadata_placeholder_files -a "handsome-snake,P000000019,C000000001,dlinssen" -u "dlinssen"

from dhpythonirodsutils import formatters

from datahubirodsruleset import icp_wrapper
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path


@make(inputs=range(4), outputs=[], handler=Output.STORE)
def replace_metadata_placeholder_files(ctx, token, project_id, collection_id, depositor):
    """
    This rule is part the mounted ingest workflow and more precisely the rule 'perform_irsync'.

    After the irsync call have been correctly executed, the physical metadata placeholders files need to be replaced.
    Those placeholder files are 0 byte files with read only access for the user.
    e.g: /mnt/ingest/zones/handsome-snake/instance.json (0 byte) -> /nlmumc/projects/P000000019/C000000001/instance.json

    The correct user-defined collection metadata are stored in the logical dropzone.
    So the project collection metadata files need to be overwritten with the ones coming from the logical dropzone.
    e.g: /nlmumc/ingest/zones/handsome-snake/instance.json  -> /nlmumc/projects/P000000019/C000000001/instance.json

    To be able to overwrite the project collection metadata files, the depositor permissions need to be escalated.
    Inherited from the project permissions, the depositor could only have 'write access' and not the necessary
    'own access'.
    e.g: ichmod own dlinssen /nlmumc/projects/P000000019/C000000001/instance.json

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The dropzone token, to locate the source collection; e.g: 'handsome-snake'
    project_id: str
        The project ID e.g: P000000001
    collection_id: str
        The collection ID e.g: C000000001
    depositor: str
        The iRODS username of the user who started the ingestion
    """
    # Suppress [B404:blacklist] Consider possible security implications associated with subprocess module.
    # subprocess is only use for subprocess.check_call to execute ichmod.
    # The ichmod checkcall has 2 user defined inputs:
    # * depositor is checked against the irods client username
    # * metadata files paths are checked with theirs respective formatter functions which calls internally
    #   the validation function 'validate_project_collection_path'
    from subprocess import CalledProcessError, check_call  # nosec

    dropzone_type = "mounted"
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)

    pc_instance_path = formatters.format_instance_collection_path(project_id, collection_id)
    pc_schema_path = formatters.format_schema_collection_path(project_id, collection_id)

    if depositor != ctx.callback.get_client_username("")["arguments"][0]:
        ctx.callback.set_post_ingestion_error_avu(
            project_id,
            collection_id,
            dropzone_path,
            "Abort replace_metadata_placeholder_files: Rule client user '{}' is not the depositor '{}'".format(
                project_id, collection_id
            ),
            depositor,
        )

    try:
        check_call(["ichmod", "own", depositor, pc_instance_path], shell=False)
        ctx.callback.msiWriteRodsLog("INFO: Updating '{}' ACL was successful".format(pc_instance_path), 0)
        check_call(["ichmod", "own", depositor, pc_schema_path], shell=False)
        ctx.callback.msiWriteRodsLog("INFO: Updating '{}' ACL was successful".format(pc_schema_path), 0)
    except CalledProcessError:
        ctx.callback.set_post_ingestion_error_avu(
            project_id,
            collection_id,
            dropzone_path,
            "Update metadata files ACL failed for '{}/{}'".format(project_id, collection_id),
            depositor,
        )

    dropzone_instance_path = formatters.format_instance_dropzone_path(token, dropzone_type)
    dropzone_schema_path = formatters.format_schema_dropzone_path(token, dropzone_type)

    ctx.callback.msiDataObjUnlink("objPath=" + pc_instance_path + "++++forceFlag=", 0)
    ctx.callback.msiDataObjUnlink("objPath=" + pc_schema_path + "++++forceFlag=", 0)

    try:
        icp_wrapper(ctx, dropzone_instance_path, pc_instance_path, project_id, True)
        icp_wrapper(ctx, dropzone_schema_path, pc_schema_path, project_id, True)
    except RuntimeError:
        ctx.callback.msiExit("-1", "ERROR: Couldn't replace the metadata placeholder files")
