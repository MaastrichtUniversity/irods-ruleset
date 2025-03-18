#DONOTCALLDIRECTLY
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def validate_and_ingest_dropzone(ctx, token, username, dropzone_type):
    """
    Executes the validation, stops execution if validation is incorrect
    Start the actual ingestion afterwards

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    token: str
        The dropzone token, e.g. 'crazy-frog'
    username: str
        The username of the depositor, e.g. dlinssen
    dropzone_type: str
        The type of dropzone, e.g. direct or mounted
    """
    project_id, validation_result, dropzone_path = validate(ctx, token, username, dropzone_type)
    
    if bool(validation_result):
        ingest(ctx, dropzone_path, project_id, username, token, dropzone_type)
    else:
        stop_ingestion(ctx, dropzone_path)


def validate(ctx, token, username, dropzone_type):
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    validation_results = json.loads(
        ctx.callback.validate_dropzone(dropzone_path, username, dropzone_type, "")["arguments"][3]
    )
    return validation_results["project_id"], validation_results["validation_result"], dropzone_path

def is_dropzone_ingestable(ctx, dropzone_path):
    is_ingestable = ctx.callback.getCollectionAVU(dropzone_path, "isIngestable", "", "", TRUE_AS_STRING)["arguments"][2]
    return formatters.format_string_to_boolean(is_ingestable)


def ingest(ctx, dropzone_path, project_id, username, token, dropzone_type):
    ctx.callback.msiWriteRodsLog(
            "Validation result OK {}. Setting status to '{}'".format(
                dropzone_path, DropzoneState.IN_QUEUE_FOR_INGESTION.value
            ),
            0,
        )
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.IN_QUEUE_FOR_INGESTION.value)
    ctx.callback.perform_ingest(project_id, username, token, dropzone_type)
    
def stop_ingestion(ctx, dropzone_path):
        message = "Metadata is incorrect or dropzone contains illegal characters"
        value = DropzoneState.WARNING_VALIDATION_INCORRECT.value
        ctx.callback.setCollectionAVU(dropzone_path, "state", value)
        ctx.callback.msiWriteRodsLog("Ingest failed of {} with error status {}".format(dropzone_path, value), 0)
        ctx.callback.msiWriteRodsLog(message, 0)
        ctx.callback.msiExit("-1", "{} for {}".format(message, dropzone_path))