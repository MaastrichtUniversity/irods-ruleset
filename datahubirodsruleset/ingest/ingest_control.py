"""Current-transfer coordination for sequential stop/restart commands."""

import json

from dhpythonirodsutils.enums import IngestAttribute, IngestStopRequestState, IngestTransferState

from datahubirodsruleset.utils import FALSE_AS_STRING

STOP_MESSAGE = "Ingest stopped by rods"


def get_ingest_avu(ctx, dropzone_path, attribute):
    return ctx.callback.getCollectionAVU(
        dropzone_path, attribute, "", "", FALSE_AS_STRING,
    )["arguments"][2]


class IngestStopped(Exception):
    """An intentional stop, deliberately not caught by RuntimeError retries."""


def get_transfer_state(ctx, dropzone_path):
    return ctx.callback.getCollectionAVU(
        dropzone_path, IngestAttribute.TRANSFER_STATE.value, "", "", FALSE_AS_STRING,
    )["arguments"][2]


def get_worker_result(ctx, dropzone_path):
    return ctx.callback.getCollectionAVU(
        dropzone_path, IngestAttribute.WORKER_RESULT.value, "", "", FALSE_AS_STRING,
    )["arguments"][2]


def request_ingest_stop(ctx, dropzone_path):
    """Set the stop flag after stop_ingest has authorized the rods caller."""
    # rods may lack a write ACL on a user-started direct dropzone. Replace the
    # initialized false flag atomically, without granting rods a new ACL.
    ctx.callback.msi_atomic_apply_metadata_operations(
        json.dumps({
            "admin_mode": True,
            "entity_name": dropzone_path,
            "entity_type": "collection",
            "operations": [
                {
                    "operation": "remove",
                    "attribute": IngestAttribute.STOP_REQUESTED.value,
                    "value": IngestStopRequestState.NOT_REQUESTED.value,
                },
                {
                    "operation": "add",
                    "attribute": IngestAttribute.STOP_REQUESTED.value,
                    "value": IngestStopRequestState.REQUESTED.value,
                },
            ],
        }),
        "",
    )


def check_stop_requested(ctx, dropzone_path):
    requested = ctx.callback.getCollectionAVU(
        dropzone_path, IngestAttribute.STOP_REQUESTED.value, "",
        IngestStopRequestState.NOT_REQUESTED.value, FALSE_AS_STRING,
    )["arguments"][2]
    if requested == IngestStopRequestState.REQUESTED.value:
        raise IngestStopped(f"{STOP_MESSAGE}: {dropzone_path}")


def require_inactive_transfer(ctx, dropzone_path):
    if get_transfer_state(ctx, dropzone_path) == IngestTransferState.ACTIVE.value:
        ctx.callback.msiExit(
            "-1", f"A transfer is still active for {dropzone_path}; wait for it to finish stopping.",
        )
