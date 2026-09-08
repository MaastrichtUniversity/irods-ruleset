# Entire collection:
# /rules/tests/run_test.sh -r restart_unarchive -a "/nlmumc/projects/P000000017/C000000001" -u service-surfarchive
# Single file:
# /rules/tests/run_test.sh -r restart_unarchive -a "/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log" -u service-surfarchive
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.tape_archival.perform_unarchive_checks import check_unarchive
from datahubirodsruleset.tape_archival.start_unarchive import queue_unarchive


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restart_unarchive(ctx, unarchival_path):
    """Restart a failed unarchive after its previous execution has stopped.

    Use the original collection or file path and the tape service account. All
    ordinary checks still apply, but unArchiveState must be error-unarchive-failed.
    The tape service account is also used as the initiator.
    """
    results = check_unarchive(ctx, unarchival_path, restart=True)
    queue_unarchive(ctx, unarchival_path, results["service_account"], results, restart=True)
