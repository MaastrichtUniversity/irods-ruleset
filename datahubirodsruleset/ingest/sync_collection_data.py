# /rules/tests/run_test.sh -r sync_collection_data -a "handsome-snake,/nlmumc/projects/P000000019/C000000001,dlinssen" -u "dlinssen"
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState, ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.core import make, Output, format_dropzone_path, format_project_path, TRUE_AS_STRING


@make(inputs=range(3), outputs=[], handler=Output.STORE)
def sync_collection_data(ctx, token, destination_collection, depositor):
    """
    This rule is part the mounted ingest workflow.
    It takes care of coping (syncing) the content of the physical drop-zone path into the destination collection.
    When the coping is done, it also calls replace_metadata_placeholder_files to update the project collection
    with the correct metadata files.

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
        The user who started the ingestion
    """
    import time

    before = 0
    dropzone_type = "mounted"
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
        ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)

    # Get the ingest resource host
    ingest_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, project_id), ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]
    ingest_resource_host = ""
    # Obtain the resource host from the specified ingest resource
    for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
        ingest_resource_host = row[0]

    # Remotely execute the actual irsync
    ctx.remoteExec(
        ingest_resource_host,
        "",
        "perform_irsync('{}', '{}', '{}')".format(
            destination_resource, token, destination_collection
        ),
        "",
    )

    ctx.callback.replace_metadata_placeholder_files(token, project_id, collection_id, depositor)

    if ingest_restart:
        after = time.time()
        difference = float(after - before) + 1
        ctx.callback.perform_ingest_post_hook(project_id, collection_id, dropzone_path, dropzone_type, str(difference))
        ctx.callback.finish_ingest(project_id, depositor, token, collection_id, ingest_resource_host, dropzone_type)
