# Only to be called directly (not from a flow) when restarting an ingestion from 'error-ingestion'!
# Always to be called as administrator
# /rules/tests/run_test.sh -r sync_collection_data -a "handsome-snake,/nlmumc/projects/P000000019/C000000001,dlinssen,direct"
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState, ProjectAVUs

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path, format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING
from datahubirodsruleset.ingest.ingest_control import (
    TRANSFER_STATE, STOP_REQUESTED, WORKER_RESULT, STOP_MESSAGE,
    IngestStopped, check_stop_requested, get_worker_result, require_inactive_transfer,
)


@make(inputs=range(4), outputs=[], handler=Output.STORE)
def sync_collection_data(ctx, token, destination_collection, depositor, dropzone_type):
    """Sync a dropzone, translating a reported stop to an iRODS rule error."""
    try:
        _sync_collection_data(ctx, token, destination_collection, depositor, dropzone_type)
    except IngestStopped as err:
        ctx.callback.msiExit("-1", str(err))


def _sync_collection_data(ctx, token, destination_collection, depositor, dropzone_type):
    """
    This rule is part the ingest workflow. It is a wrapper around perform_irsync with some additional error handling and restart capabilities.
    It takes care of coping (syncing) the content of the physical (mounted) or virtual (direct) drop-zone path into the destination collection.
    MOUNTED: When the coping is done, it also calls replace_metadata_placeholder_files to update the project collection
    with the correct metadata files. (not necessary for direct)

    In case of failed ingest and an admin want to restart the rule:
        * It can be executed on any iRODS server
            * The rule needs physical access to the source collection to perform the 'irsync' call.
        * If the dropzone state AVU is 'error_ingestion', the rule 'finish_ingest' will be called afterward.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The dropzone token, to locate the source collection; e.g: 'handsome-snake'
    destination_collection: str
        The absolute path to the newly created project collection; e.g: '/nlmumc/projects/P000000018/C000000001'
    depositor: str
        The iRODS username of the user who started the ingestion
    dropzone_type: str
        The type of dropzone to be ingested (mounted or direct)
    """
    import time

    before = 0
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)

    project_id = formatters.get_project_id_from_project_collection_path(destination_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(destination_collection)

    destination_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]

    # Query dropzone state AVU and to call the rule finish_ingest if the state is 'error_ingestion' (= ingest restart)
    ingest_restart = False
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    if state == DropzoneState.ERROR_INGESTION.value:
        ingest_restart = True
        before = time.time()
        ctx.callback.msiWriteRodsLog(f"Restarting ingestion {dropzone_path}", 0)
        ctx.callback.msiSetACL("default", "admin:own", "rods", destination_collection)
        if dropzone_type == "direct":
            ctx.callback.msiSetACL("default", "admin:own", "rods", dropzone_path)
    else:
        require_inactive_transfer(ctx, dropzone_path)

    # Get the ingest resource host
    ingest_resource_host = ctx.callback.get_dropzone_resource_host(dropzone_type, project_id, "")["arguments"][2]

    ctx.callback.setCollectionAVU(dropzone_path, STOP_REQUESTED, FALSE_AS_STRING)
    ctx.callback.remove_collection_attribute_value(dropzone_path, WORKER_RESULT)
    ctx.callback.setCollectionAVU(dropzone_path, TRANSFER_STATE, "active")
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)
    completed_state = "finished"
    worker_returned = False

    # Execute the irsync call remotely for mounted ingests, as it needs access to the physical path
    try:
        try:
            if dropzone_type == "mounted":
                ctx.remoteExec(
                    ingest_resource_host,
                    "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
                    f"perform_irsync('{destination_resource}', '{token}', '{destination_collection}', "
                    f"'{dropzone_type}', '{str(ingest_restart).lower()}')",
                    "",
                )
            elif dropzone_type == "direct":
                ctx.callback.perform_irsync(
                    destination_resource, token, destination_collection, dropzone_type,
                    str(ingest_restart).lower(),
                )
            worker_returned = True
        except RuntimeError as err:
            if get_worker_result(ctx, dropzone_path) == "stopped":
                raise IngestStopped(f"{STOP_MESSAGE}: {dropzone_path}") from err
            ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.ERROR_INGESTION.value)
            raise RuntimeError(f"Error syncing collection data for {dropzone_path}") from err
        # Cover requests arriving while the worker's success is being returned.
        check_stop_requested(ctx, dropzone_path)
    except IngestStopped as err:
        if dropzone_type == "mounted" and get_worker_result(ctx, dropzone_path) != "stopped":
            ctx.remoteExec(
                ingest_resource_host,
                "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
                f"set_dropzone_cifs_acl('{token}', 'write')",
                "",
            )
        try:
            # This existing handler sets error-ingestion, submits a support
            # request, and unconditionally exits with RuntimeError.
            ctx.callback.set_ingestion_error_avu(dropzone_path, str(err), project_id, depositor)
        except RuntimeError:
            # The existing handler exits with RuntimeError even on completion.
            pass
        state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
        if state != DropzoneState.ERROR_INGESTION.value:
            raise RuntimeError(f"Stop handling did not set error-ingestion for {dropzone_path}") from err
        completed_state = "stopped"
        raise
    finally:
        # A failed remoteExec may leave its worker running. Keep active unless
        # the callback returned or the worker reported that it has exited.
        if worker_returned or get_worker_result(ctx, dropzone_path) in ("stopped", "exited"):
            ctx.callback.setCollectionAVU(dropzone_path, TRANSFER_STATE, completed_state)

    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    if state == DropzoneState.ERROR_INGESTION.value:
        ctx.callback.msiExit("-1", f"Stop sync_collection_data for {dropzone_path}'")

    if dropzone_type == "mounted":
        ctx.callback.replace_metadata_placeholder_files(token, project_id, collection_id, depositor)

    if ingest_restart:
        after = time.time()
        difference = float(after - before) + 1
        ctx.callback.perform_ingest_post_hook(
            project_id, collection_id, dropzone_path, dropzone_type, str(difference), depositor
        )
        ctx.callback.finish_ingest(project_id, depositor, token, collection_id, dropzone_type)
