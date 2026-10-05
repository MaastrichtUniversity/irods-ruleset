"""Maintenance window metadata and size-based ingest lead times."""

import re

from datahubirodsruleset.utils import FALSE_AS_STRING


MAINTENANCE_COLLECTION = "/nlmumc/ingest/zones"
MAINTENANCE_START = "maintenanceStart"
MAINTENANCE_END = "maintenanceEnd"
HOUR = 60 * 60
GIB = 1024 ** 3
MAX_LEAD_SECONDS = 120 * HOUR


def parse_window(start, end):
    if not re.fullmatch(r"[0-9]+", start) or not re.fullmatch(r"[0-9]+", end):
        raise ValueError("Maintenance timestamps must be UTC Unix seconds")
    start, end = int(start), int(end)
    if end <= start:
        raise ValueError("Maintenance end must be after its start")
    return start, end


def get_window(ctx):
    start = ctx.callback.getCollectionAVU(
        MAINTENANCE_COLLECTION, MAINTENANCE_START, "", "", FALSE_AS_STRING
    )["arguments"][2]
    end = ctx.callback.getCollectionAVU(
        MAINTENANCE_COLLECTION, MAINTENANCE_END, "", "", FALSE_AS_STRING
    )["arguments"][2]
    if not start and not end:
        return None
    try:
        return parse_window(start, end)
    except ValueError as error:
        ctx.callback.msiExit("-1", f"Invalid ingest maintenance window: {error}")


def lead_seconds(size_bytes):
    for size_gib, hours in ((500, 120), (400, 96), (300, 72), (200, 48), (100, 24)):
        if size_bytes >= size_gib * GIB:
            return hours * HOUR
    return 8 * HOUR
