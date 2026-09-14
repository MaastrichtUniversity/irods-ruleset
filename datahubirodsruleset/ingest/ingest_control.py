"""Current-transfer coordination for sequential stop/restart commands."""

import json

from datahubirodsruleset.utils import FALSE_AS_STRING, TRUE_AS_STRING

# Coordinator: active until worker exit is confirmed and failure handling ends.
TRANSFER_STATE = "ingestTransferState"
# Coordinator resets this flag before starting; stop_ingest sets it as rods.
STOP_REQUESTED = "ingestStopRequested"
# Worker: stopped after cancellation handling, otherwise exited (also on error).
WORKER_RESULT = "ingestWorkerResult"
STOP_MESSAGE = "Ingest stopped by rods"


class IngestStopped(Exception):
    """An intentional stop, deliberately not caught by RuntimeError retries."""


def get_transfer_state(ctx, dropzone_path):
    return ctx.callback.getCollectionAVU(dropzone_path, TRANSFER_STATE, "", "", FALSE_AS_STRING)["arguments"][2]


def get_worker_result(ctx, dropzone_path):
    return ctx.callback.getCollectionAVU(dropzone_path, WORKER_RESULT, "", "", FALSE_AS_STRING)["arguments"][2]


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
                {"operation": "remove", "attribute": STOP_REQUESTED, "value": FALSE_AS_STRING},
                {"operation": "add", "attribute": STOP_REQUESTED, "value": TRUE_AS_STRING},
            ],
        }),
        "",
    )


def check_stop_requested(ctx, dropzone_path):
    requested = ctx.callback.getCollectionAVU(
        dropzone_path, STOP_REQUESTED, "", FALSE_AS_STRING, FALSE_AS_STRING,
    )["arguments"][2]
    if requested == TRUE_AS_STRING:
        raise IngestStopped(f"{STOP_MESSAGE}: {dropzone_path}")


def require_inactive_transfer(ctx, dropzone_path):
    if get_transfer_state(ctx, dropzone_path) == "active":
        ctx.callback.msiExit(
            "-1", f"A transfer is still active for {dropzone_path}; wait for it to finish stopping.",
        )
