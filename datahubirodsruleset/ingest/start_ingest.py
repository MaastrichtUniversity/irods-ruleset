# /rules/tests/run_test.sh -r start_ingest -a "dlinssen,handsome-snake,direct" -u "dlinssen"
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path


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

    pre_ingest_tasks = json.loads(
        ctx.callback.validate_dropzone(dropzone_path, depositor, dropzone_type, "")["arguments"][3]
    )
    project_id = pre_ingest_tasks["project_id"]
    title = pre_ingest_tasks["title"]
    validation_result = pre_ingest_tasks["validation_result"]

    # Python2.7 default encoding is ASCII, so we need to enforce UFT-8 encoding
    title = title.encode("utf-8")
    depositor = depositor.encode("utf-8")
    token = token.encode("utf-8")

    if formatters.format_string_to_boolean(validation_result):
        ctx.callback.msiWriteRodsLog(
            "Validation result OK {}. Setting status to '{}'".format(
                dropzone_path, DropzoneState.IN_QUEUE_FOR_INGESTION.value
            ),
            0,
        )
        ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.IN_QUEUE_FOR_INGESTION.value)

        ctx.delayExec(
            "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            "perform_{}_ingest('{}', '{}', '{}', '{}')".format(dropzone_type, project_id, title, depositor, token),
            "",
        )
    else:
        message = "Metadata is incorrect"
        value = DropzoneState.WARNING_VALIDATION_INCORRECT.value
        ctx.callback.setCollectionAVU(dropzone_path, "state", value)
        ctx.callback.msiWriteRodsLog("Ingest failed of {} with error status {}".format(dropzone_path, value), 0)
        ctx.callback.msiWriteRodsLog(message, 0)
        ctx.callback.msiExit("-1", "{} for {}".format(message, dropzone_path))
