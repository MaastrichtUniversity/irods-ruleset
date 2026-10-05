# /rules/tests/run_test.sh -r set_ingest_maintenance_window -a "2000000000,2000086400" -u rods
# Ubuntu: current time to epoch seconds: date +%s
# Ubuntu: epoch seconds to UTC time: date -u -d @2000000000
"""Set the zone-wide ingest maintenance window."""

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.ingest.maintenance import (
    MAINTENANCE_COLLECTION, MAINTENANCE_END, MAINTENANCE_START, parse_window,
)


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def set_ingest_maintenance_window(ctx, start, end):
    """Set UTC Unix-second start and end timestamps; callable only by rods."""
    if ctx.callback.get_client_username("")["arguments"][0] != "rods":
        return ctx.callback.msiExit("-1", "Only rods may set the ingest maintenance window")
    try:
        start, end = parse_window(start, end)
    except ValueError as error:
        return ctx.callback.msiExit("-1", str(error))

    ctx.callback.setCollectionAVU(MAINTENANCE_COLLECTION, MAINTENANCE_START, str(start))
    ctx.callback.setCollectionAVU(MAINTENANCE_COLLECTION, MAINTENANCE_END, str(end))
