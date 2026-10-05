# /rules/tests/run_test.sh -r get_ingest_maintenance_window -u rods -j
# Ubuntu: current time to epoch seconds: date +%s
# Ubuntu: epoch seconds to UTC time: date -u -d @2000000000
"""Get the zone-wide ingest maintenance window."""

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.ingest.maintenance import MAINTENANCE_END, MAINTENANCE_START, get_window


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_ingest_maintenance_window(ctx):
    """Return UTC Unix-second timestamps, or null values when no window is set."""
    window = get_window(ctx)
    start, end = window if window is not None else (None, None)
    return {MAINTENANCE_START: start, MAINTENANCE_END: end}
