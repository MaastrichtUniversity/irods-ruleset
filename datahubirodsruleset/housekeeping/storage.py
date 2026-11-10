# /rules/tests/run_test.sh -r initialize_housekeeping -a "passRescUM01,31" -j
"""Initialize private housekeeping storage and share catalog/report helpers."""

import json
import re

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import in_conditions, query_value


REPORT_COLLECTION = "/nlmumc/home/rods/housekeeping"
RUNS_COLLECTION = REPORT_COLLECTION + "/runs"
DEFAULT_RESOURCE = "passRescUM01"
DEFAULT_RETENTION_DAYS = "31"
TERMINAL_STATES = {"completed", "partial", "failed"}


def _write_report_json(ctx, path, resource, document):
    descriptor = ctx.callback.msiDataObjCreate(
        path, f"destRescName={resource}++++forceFlag=", 0,
    )["arguments"][2]
    try:
        ctx.callback.msiDataObjWrite(descriptor, json.dumps(document, indent=2), 0)
    finally:
        ctx.callback.msiDataObjClose(descriptor, 0)


def _require_rods(ctx):
    if ctx.callback.get_client_username("")["arguments"][0] != "rods":
        raise RuntimeError("Housekeeping report administration can only be called by RODS")


def _metadata(ctx, path):
    metadata = {}
    for attribute, value, _ in row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
        f"COLL_NAME = {query_value(path)}", AS_LIST, ctx.callback
    ):
        # Ambiguous metadata must never make a run eligible for deletion.
        metadata[attribute] = value if attribute not in metadata else None
    return metadata


def _positive_integer(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value) or int(value) < 1:
        raise ValueError("Expected a positive integer")
    return int(value)


def _private_collection(ctx, path):
    if not _collection_exists(ctx, path):
        ctx.callback.msiCollCreate(path, 0, 0)
    ctx.callback.msiSetACL("default", "noinherit", "", path)
    ctx.callback.msiSetACL("default", "own", "rods", path)
    identifiers = [row[0] for row in row_iterator(
        "COLL_ACCESS_USER_ID", f"COLL_NAME = {query_value(path)}", AS_LIST, ctx.callback
    )]
    for condition in in_conditions("USER_ID", identifiers):
        for name, zone in row_iterator("USER_NAME, USER_ZONE", condition, AS_LIST, ctx.callback):
            if (name, zone) != ("rods", "nlmumc"):
                ctx.callback.msiSetACL("default", "null", f"{name}#{zone}", path)


def _run_path(run_id):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9a-f]{32}", run_id):
        raise RuntimeError("Invalid housekeeping run ID")
    return RUNS_COLLECTION + "/" + run_id


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def initialize_housekeeping(ctx, report_resource, retention_days):
    """Create private report/runs collections and configure resource and retention.

    Empty arguments preserve existing settings, or use passRescUM01 / 31 days
    on first initialization. Does not create physical files or schedule work.
    """
    return _initialize_housekeeping(ctx, report_resource, retention_days)


def _initialize_housekeeping(ctx, report_resource, retention_days):
    _require_rods(ctx)
    metadata = _metadata(ctx, REPORT_COLLECTION)
    resource = report_resource or metadata.get("reportResource", DEFAULT_RESOURCE)
    days = retention_days or metadata.get("reportRetentionDays", DEFAULT_RETENTION_DAYS)
    days = _validate_configuration(ctx, resource, days)

    for path in (REPORT_COLLECTION, RUNS_COLLECTION):
        _private_collection(ctx, path)
    ctx.callback.setCollectionAVU(REPORT_COLLECTION, "reportResource", resource)
    ctx.callback.setCollectionAVU(REPORT_COLLECTION, "reportRetentionDays", str(days))
    return {"report_collection": REPORT_COLLECTION, "runs_collection": RUNS_COLLECTION,
            "report_resource": resource, "report_retention_days": days}


def _validate_configuration(ctx, resource, days):
    try:
        days = _positive_integer(days)
    except ValueError as error:
        raise RuntimeError("reportRetentionDays must be a positive integer") from error
    if not isinstance(resource, str) or not resource or not list(row_iterator(
        "RESC_NAME", f"RESC_NAME = {query_value(resource)}", AS_LIST, ctx.callback
    )):
        raise RuntimeError(f"Report resource does not exist: {resource!r}")

    return days


def _collection_exists(ctx, path):
    return bool(list(row_iterator("COLL_NAME", f"COLL_NAME = {query_value(path)}", AS_LIST, ctx.callback)))


def _ensure_housekeeping(ctx):
    """Initialize absent storage; validate existing storage without changing it."""
    if not _collection_exists(ctx, REPORT_COLLECTION):
        return _initialize_housekeeping(ctx, "", "")["report_resource"]
    metadata = _metadata(ctx, REPORT_COLLECTION)
    resource = metadata.get("reportResource")
    if not resource:
        raise RuntimeError("Initialize housekeeping with a reportResource before running housekeeping")
    _validate_configuration(ctx, resource, metadata.get("reportRetentionDays"))
    if not _collection_exists(ctx, RUNS_COLLECTION):
        raise RuntimeError("Initialize housekeeping to create the missing runs collection")
    return resource
