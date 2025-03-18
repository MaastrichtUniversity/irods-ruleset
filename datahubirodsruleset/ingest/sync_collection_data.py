# Only to be called directly (not from a flow) when restarting an ingestion from 'error-ingestion'!
# Always to be called as administrator
# /rules/tests/run_test.sh -r sync_collection_data -a "handsome-snake,/nlmumc/projects/P000000019/C000000001,dlinssen,direct"
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState, ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path, format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=range(4), outputs=[], handler=Output.STORE)
def sync_collection_data(ctx, token, destination_collection, depositor, dropzone_type):
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
        ctx.callback.msiWriteRodsLog("Restarting ingestion {}".format(dropzone_path), 0)
        # If we are restarting the ingestion, make sure that the rods user has access to both the source and destination collection
        ctx.callback.msiSetACL("default", "admin:own", "rods", destination_collection)
        if dropzone_type == "direct":
            ctx.callback.msiSetACL("default", "admin:own", "rods", dropzone_path)
        ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)

    # Get the ingest resource host
    ingest_resource_host = ctx.callback.get_dropzone_resource_host(dropzone_type, project_id, "")["arguments"][2]

    # Execute the irsync call remotely for mounted ingests, as it needs access to the physical path
    if dropzone_type == "mounted":
        # Remotely execute the actual irsync
        ctx.remoteExec(
            ingest_resource_host,
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            "perform_irsync('{}', '{}', '{}', '{}', '{}')".format(
                destination_resource, token, destination_collection, depositor, dropzone_type
            ),
            "",
        )
    # Execute the irsync on iCAT locally if its a direct ingest, since it's all virtual
    elif dropzone_type == "direct":
        ctx.callback.perform_irsync(destination_resource, token, destination_collection, depositor, dropzone_type)

    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    if state == DropzoneState.ERROR_INGESTION.value:
        ctx.callback.msiExit("-1", "Stop sync_collection_data for {}'".format(dropzone_path))

    if dropzone_type == "mounted":
        ctx.callback.replace_metadata_placeholder_files(token, project_id, collection_id, depositor)

    if ingest_restart:
        after = time.time()
        difference = float(after - before) + 1
        ctx.callback.perform_ingest_post_hook(
            project_id, collection_id, dropzone_path, dropzone_type, str(difference), depositor
        )
        ctx.callback.finish_ingest(project_id, depositor, token, collection_id, dropzone_type)
