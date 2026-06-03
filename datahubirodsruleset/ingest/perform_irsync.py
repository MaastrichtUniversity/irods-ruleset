# Part of the ingest workflow. To use, call the rule sync_collection_data
# Suppress [B404:blacklist] Consider possible security implications associated with subprocess module.
# subprocess is only used for check_call to execute irsync.
# The irsync check_call has 3 variable inputs:
# * destination_resource, queried directly from iCAT with getCollectionAVU ProjectAVUs.RESOURCE
# * source_collection, token is validated with format_dropzone_path & check the ACL with getCollectionAVU state
# * destination_collection, validated with the formatter functions get_*_from_project_collection_path
from subprocess import CalledProcessError, check_call  # nosec

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path
from datahubirodsruleset.utils import retry_runtime_error

def _clean_failed_replicas(ctx, destination_collection):
    """
    Remove all data objects under destination_collection whose replica status is not
    '1' (good), so that a subsequent irsync can recreate them from scratch.

    Replicas with status '2' are first reset to '0' via 'iadmin modrepl' because
    iRODS treats them as authoritative and may refuse to overwrite them otherwise.
    Each unique data object is deleted at most once even if multiple failed replicas
    are reported for it.
    """
    # Collect all failed replicas grouped by data object path first, so that every
    # locked replica (status '2') of the same object is reset to '0' before we attempt
    # deletion.  Attempting to delete while a sibling replica is still in state '2'
    # would be rejected by iRODS.
    failed_replicas = {}
    for result in row_iterator(
        "COLL_NAME, DATA_NAME, DATA_REPL_NUM, DATA_REPL_STATUS",
        f"COLL_NAME LIKE '{destination_collection}%' AND DATA_REPL_STATUS != '1'",
        AS_LIST,
        ctx.callback,
    ):
        full_data_obj_path = f"{result[0]}/{result[1]}"
        repl_num = result[2]
        repl_status = result[3]
        failed_replicas.setdefault(full_data_obj_path, []).append((repl_num, repl_status))

    for full_data_obj_path, replicas in failed_replicas.items():
        for repl_num, repl_status in replicas:
            # repl_status '2' means locked replica, which can happen if a previous irsync partially succeeded and got interrupted (e.g. by a timeout).
            # locked files cant be removed by iRODS, and they will also cause subsequent irsync calls to fail, so we reset the status to '0' (stale) to allow cleanup and retry.
            if repl_status == "2":
                ctx.callback.msiWriteRodsLog(
                    f"INFO: Resetting stale replica {full_data_obj_path} (repl {repl_num}) status to 0 before removal",
                    0,
                )
                try:
                    check_call(
                        [
                            "iadmin",
                            "modrepl",
                            "logical_path",
                            full_data_obj_path,
                            "replica_number",
                            repl_num,
                            "DATA_REPL_STATUS",
                            "0",
                        ],
                        shell=False,
                    )
                except CalledProcessError as err:
                    ctx.callback.msiWriteRodsLog(
                        f"WARNING: iadmin modrepl failed for {full_data_obj_path} replica {repl_num} (retcode {err.returncode})",
                        0,
                    )

        ctx.callback.msiWriteRodsLog(
            f"INFO: Removing failed data object {full_data_obj_path}", 0
        )
        ctx.callback.msiDataObjUnlink(f"objPath={full_data_obj_path}++++forceFlag=", 0)

    return len(failed_replicas)


def _get_resource_child_count(ctx, resource_name):
    """Return the number of direct child resources of resource_name."""
    resc_id = None
    for result in row_iterator("RESC_ID", f"RESC_NAME = '{resource_name}'", AS_LIST, ctx.callback):
        resc_id = result[0]
    if resc_id is None:
        return 0
    for result in row_iterator("COUNT(RESC_ID)", f"RESC_PARENT = '{resc_id}'", AS_LIST, ctx.callback):
        return int(result[0])
    return 0


def _check_replica_count(ctx, destination_collection, destination_resource):
    """
    Verify that every data object in destination_collection has the expected number
    of replicas.  The expected count equals the number of direct children of
    destination_resource, or 1 for a leaf resource.

    Objects with a mismatched replica count are removed so a subsequent irsync can
    recreate them cleanly.

    Returns the number of objects removed.
    """
    child_count = _get_resource_child_count(ctx, destination_resource)
    expected_replica_count = child_count if child_count > 0 else 1

    under_replicated = []
    for result in row_iterator(
        "COLL_NAME, DATA_NAME, COUNT(DATA_REPL_NUM)",
        f"COLL_NAME LIKE '{destination_collection}%'",
        AS_LIST,
        ctx.callback,
    ):
        full_data_obj_path = f"{result[0]}/{result[1]}"
        actual_replica_count = int(result[2])
        if actual_replica_count != expected_replica_count:
            under_replicated.append((full_data_obj_path, actual_replica_count))

    for full_data_obj_path, actual_replica_count in under_replicated:
        ctx.callback.msiWriteRodsLog(
            f"INFO: Removing under-replicated data object {full_data_obj_path}"
            f" (expected {expected_replica_count} replica(s), found {actual_replica_count})",
            0,
        )
        ctx.callback.msiDataObjUnlink(f"objPath={full_data_obj_path}++++forceFlag=", 0)

    return len(under_replicated)


def _run_irsync(source_collection, destination_collection, destination_resource):
    """
    Execute a single irsync call, converting CalledProcessError to RuntimeError
    so that retry_runtime_error can catch transient failures uniformly.
    """
    try:
        check_call(
            [
                "irsync",
                "-K",
                "-v",
                "-R",
                destination_resource,
                "-r",
                source_collection,
                "i:" + destination_collection,
            ],
            shell=False,
        )
    except CalledProcessError as err:
        raise RuntimeError(f"irsync: cmd '{err.cmd}' retcode '{err.returncode}'") from err


@make(inputs=range(5), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, destination_resource, token, destination_collection, depositor, dropzone_type):
    """
    This rule is part the ingest workflow.
    It takes care of actually copying (syncing) the content of the drop-zone into the destination collection.

    Should not be called directly, instead call the wrapper function sync_collection_data.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    destination_resource: str
        The resource that the ingestion should end up in; e.g. 'passRescUM01'
    token: str
        The dropzone token, to locate the source collection; e.g: 'handsome-snake'
    destination_collection: str
        The absolute path to the newly created project collection; e.g: '/nlmumc/projects/P000000018/C000000001'
    depositor: str
        The iRODS username of the user who started the ingestion
    dropzone_type: str
        The type of dropzone to be ingested (mounted or direct)
    """
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    if dropzone_type == "mounted":
        source_collection = f"/mnt/ingest/zones/{token}"
        # Revoke the user CIFS ACL on the mounted network dropzone folder
        ctx.callback.set_dropzone_cifs_acl(token, "null")
    elif dropzone_type == "direct":
        # We need to prefix the dropzone path with 'i:' to indicate to iRODS that it is an iRODS - iRODS sync
        source_collection = f"i:{dropzone_path}"

    def _irsync_with_cleanup():
        try:
            _run_irsync(source_collection, destination_collection, destination_resource)
        except RuntimeError:
            # Clean up all issues in one pass so the retry starts from a consistent state.
            _clean_failed_replicas(ctx, destination_collection)
            _check_replica_count(ctx, destination_collection, destination_resource)
            raise

        # irsync can report success while silently leaving the destination in a
        # partial state.  Run both checks together so a single retry is sufficient
        # to address all issues found, regardless of which combination is present.
        cleaned_count = _clean_failed_replicas(ctx, destination_collection)
        under_replicated_count = _check_replica_count(ctx, destination_collection, destination_resource)
        if cleaned_count + under_replicated_count > 0:
            raise RuntimeError(
                f"irsync completed without error but found issues with "
                f"{cleaned_count + under_replicated_count} data object(s) in {destination_collection}"
            )

    operation_name = f"irsync {source_collection} -> {destination_collection}"
    success = retry_runtime_error(
        ctx,
        operation_name,
        _irsync_with_cleanup,
    )

    if success:
        ctx.callback.msiWriteRodsLog(
            f"INFO: Ingest collection data '{source_collection}' was successful", 0
        )
    else:
        if dropzone_type == "mounted":
            # Re-set the user CIFS ACL on the mounted network dropzone folder
            ctx.callback.set_dropzone_cifs_acl(token, "write")
        # Perform an MSIEXIT here. If this rule is called from the 'perform_ingest' part of the ingest flow,
        # then this error should be caught as a "RuntimeError" and should translate into the creation of a Jira ticket
        # and setting the error-ingestion AVU.
        # If the rule is called by directly calling 'sync_collection_data', then this will just stop execution and *not*
        # create a Jira ticket and *not* set the error-ingestion AVU.
        ctx.callback.msiExit(
            "-1",
            f"Error while performing perform_irsync towards '{destination_collection}:{destination_resource}'",
        )
