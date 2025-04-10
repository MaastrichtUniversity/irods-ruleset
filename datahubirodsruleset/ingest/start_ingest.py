# To be called as an admin at all times
# /rules/tests/run_test.sh -r start_ingest -a "dlinssen,handsome-snake,direct"
from dhpythonirodsutils.enums import DropzoneState
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def start_ingest(ctx, depositor, token, dropzone_type):
    """
    Start to ingest
       Irods pre-ingest checks
       Metadata pre-ingest checks
        If those went well, call perform ingest

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    depositor: str
        The iRODS username of the user who started the ingestion, e.g: 'dlinssen'
    token: str
        The token, eg 'crazy-frog'
    dropzone_type: str
        The type of dropzone, 'mounted' or 'direct'
    """
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    # Check for valid state to start ingestion
    check_if_state_is_valid_to_start_ingestion(ctx, dropzone_path)
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.IN_QUEUE_FOR_VALIDATION.value)

    ctx.delayExec(
        "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        "process_dropzone('{}', '{}', '{}')".format(token, depositor, dropzone_type),
        "",
    )


def check_if_state_is_valid_to_start_ingestion(ctx, dropzone_path):
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", TRUE_AS_STRING)["arguments"][2]
    ingestable = ctx.callback.is_dropzone_state_ingestable(state, "")["arguments"][1]
    if not formatters.format_string_to_boolean(ingestable):
        ctx.callback.msiExit("-1", "Invalid state to start ingestion.")
