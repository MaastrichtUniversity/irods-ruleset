# DONOTCALLDIRECTLY
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DropzoneState

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_dropzone_path
from datahubirodsruleset.utils import TRUE_AS_STRING
from datahubirodsruleset.ingest.ingest_control import get_ingest_avu


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def process_dropzone(ctx, token, username, dropzone_type):
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
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    state = get_ingest_avu(ctx, dropzone_path, "state")
    if not state or state in (DropzoneState.INGESTED.value, DropzoneState.ERROR_POST_INGESTION.value):
        return
    if get_ingest_avu(ctx, dropzone_path, "destination"):
        ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.ERROR_INGESTION.value)
        ctx.callback.msiWriteRodsLog(f"Ingest already has a destination for {dropzone_path}; admin restart required", 0)
        return
    if state not in ("in-queue-for-validation", "validating", "in-queue-for-ingestion"):
        return
    validation_results, dropzone_path = validate(ctx, token, username, dropzone_type)

    if not validation_results["validation_errors"]:
        ingest(ctx, dropzone_path, validation_results["project_id"], username, token, dropzone_type)
    else:
        stop_ingestion(ctx, dropzone_path, validation_results["validation_errors"])


def validate(ctx, token, username, dropzone_type):
    dropzone_path = format_dropzone_path(ctx, token, dropzone_type)
    validation_results = json.loads(
        ctx.callback.validate_dropzone(dropzone_path, username, dropzone_type, "")["arguments"][3]
    )
    return validation_results, dropzone_path


def is_dropzone_ingestable(ctx, dropzone_path):
    is_ingestable = ctx.callback.getCollectionAVU(dropzone_path, "isIngestable", "", "", TRUE_AS_STRING)["arguments"][2]
    return formatters.format_string_to_boolean(is_ingestable)


def ingest(ctx, dropzone_path, project_id, username, token, dropzone_type):
    ctx.callback.msiWriteRodsLog(
        f"Validation result OK {dropzone_path}. Setting status to '{DropzoneState.IN_QUEUE_FOR_INGESTION.value}'",
        0,
    )
    ctx.callback.setCollectionAVU(dropzone_path, "state", DropzoneState.IN_QUEUE_FOR_INGESTION.value)
    ctx.callback.perform_ingest(project_id, username, token, dropzone_type)


def stop_ingestion(ctx, dropzone_path, validation_errors):
    if any(["unsupported" in element for element in validation_errors]):
        message = "Dropzone contains unsupported characters"
        value = DropzoneState.WARNING_UNSUPPORTED_CHARACTER.value
    else:
        message = "Dropzone validation failed"
        value = DropzoneState.WARNING_VALIDATION_INCORRECT.value
    for validation_error in validation_errors:
        ctx.callback.msiWriteRodsLog(
            f"Validation error '{validation_error}' occurred for dropzone '{dropzone_path}'", 0
        )

    ctx.callback.setCollectionAVU(dropzone_path, "state", value)
    ctx.callback.msiWriteRodsLog(f"Ingest failed of {dropzone_path} with error status {value}", 0)
    ctx.callback.msiWriteRodsLog(message, 0)
    ctx.callback.msiExit("-1", f"{message} for {dropzone_path}")
