# /rules/tests/run_test.sh -r restart_archive -a "/nlmumc/projects/P000000017/C000000001" -u service-surfarchive
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.tape_archival.perform_archive_checks import check_archive
from datahubirodsruleset.tape_archival.start_archive import queue_archive


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restart_archive(ctx, archival_path):
    """Restart a failed archive after its previous execution has stopped.

    Use the original collection path and the tape service account. All ordinary
    archive checks still apply, but archiveState must be error-archive-failed.
    The tape service account is also used as the initiator.
    """
    results = check_archive(ctx, archival_path, restart=True)
    queue_archive(ctx, archival_path, results["service_account"], results, restart=True)
