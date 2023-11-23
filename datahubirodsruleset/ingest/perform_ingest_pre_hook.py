from dhpythonirodsutils.enums import ProjectAVUs, DropzoneState
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error
import json
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path, format_human_bytes, format_project_collection_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1, 2, 3, 4], outputs=[5], handler=Output.STORE)
def perform_ingest_pre_hook(ctx, project_id, dropzone_path, token, depositor, dropzone_type):
    """
    This rule is part the ingestion workflow.
    Perform the preliminary common tasks for both 'mounted' and 'direct' ingest.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The project id, e.g: P00000010
    dropzone_path: str
        The dropzone absolute path
    token: str
        The token of the dropzone
    depositor: str
        The iRODS username of the user who started the ingestion
    dropzone_type: str
        The type of dropzone

    Returns
    -------
    dict
        collection_id, destination_collection & ingest_resource_host
    """
    ctx.callback.msiWriteRodsLog("Starting ingestion {}".format(dropzone_path), 0)
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.INGESTING.value)

    title = ctx.callback.getCollectionAVU(dropzone_path, "title", "", "", TRUE_AS_STRING)["arguments"][2]

    try:
        collection_id = ctx.callback.create_project_collection(project_id, title, "")["arguments"][2]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("Failed creating projectCollection", 0)
        ctx.callback.set_ingestion_error_avu(dropzone_path, "Error creating projectCollection", project_id, depositor)

    destination_project_collection_path = format_project_collection_path(ctx, project_id, collection_id)

    ctx.callback.msiWriteRodsLog("Ingesting {} to {}".format(dropzone_path, destination_project_collection_path), 0)
    ctx.callback.setCollectionAVU(dropzone_path, "destination", collection_id)

    if dropzone_type == "direct":
        ingest_resource_host = ctx.callback.get_direct_ingest_resource_host("")["arguments"][0]
    else:
        ingest_resource = ctx.callback.getCollectionAVU(
            format_project_path(ctx, project_id), ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        # Obtain the resource host from the specified ingest resource
        for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
            ingest_resource_host = row[0]

    ctx.callback.msiWriteRodsLog("DEBUG: Resource remote host {}".format(ingest_resource_host), 0)

    total_size = ""
    destination_resource = ""
    try:
        ctx.remoteExec(
            ingest_resource_host,
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            "save_dropzone_pre_ingest_info('{}', '{}', '{}', '{}')".format(
                token, collection_id, depositor, dropzone_type
            ),
            "",
        )
        total_size = ctx.callback.getCollectionAVU(dropzone_path, "totalSize", "", "", TRUE_AS_STRING)["arguments"][2]
        destination_resource = ctx.callback.getCollectionAVU(
            format_project_path(ctx, project_id), ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("Failed creating dropzone pre-ingest information", 0)
        ctx.callback.set_ingestion_error_avu(
            dropzone_path, "Failed creating dropzone pre-ingest information", project_id, depositor
        )

    ctx.callback.msiWriteRodsLog(
        "DEBUG: dropzone pre-ingest information created on {} for {}".format(ingest_resource_host, token), 0
    )

    ctx.callback.msiWriteRodsLog(
        "Starting the ingestion of {} to {} ({})({})".format(
            dropzone_path,
            destination_project_collection_path,
            destination_resource,
            str(format_human_bytes(total_size)),
        ),
        0,
    )
    return {
        "collection_id": collection_id,
        "destination_collection": destination_project_collection_path,
        "ingest_resource_host": ingest_resource_host,
    }
