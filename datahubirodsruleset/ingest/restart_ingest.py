# To be called as an admin at all times
# /rules/tests/run_test.sh -r restart_ingest -a "handsome-snake,direct"
from dhpythonirodsutils.enums import DropzoneState
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path, format_project_collection_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def restart_ingest(ctx, token, dropzone_type):
    """
    Restart ingestion
       Irods pre-ingest checks
       Metadata pre-ingest checks
        If those went well, call sync_collection_data

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The token, eg 'crazy-frog'
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'
    """
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    check_if_state_is_valid_to_restart_ingestion(ctx, dropzone_path)
    destination_collection = ctx.callback.getCollectionAVU(dropzone_path, "destination", "", "", TRUE_AS_STRING)["arguments"][2]
    destination_project = ctx.callback.getCollectionAVU(dropzone_path, "project", "", "", TRUE_AS_STRING)["arguments"][2]
    project_collection_path = format_project_collection_path(ctx, destination_project, destination_collection)
    creator = ctx.callback.getCollectionAVU(dropzone_path, "creator", "", "", TRUE_AS_STRING)["arguments"][2]

    ctx.delayExec(
        "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        f"sync_collection_data('{token}', '{project_collection_path}', '{creator}', '{dropzone_type}')",
        "",
    )


def check_if_state_is_valid_to_restart_ingestion(ctx, dropzone_path):
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    if state != "error-ingestion":
        ctx.callback.msiExit("-1", "Invalid state to restart ingestion.")
