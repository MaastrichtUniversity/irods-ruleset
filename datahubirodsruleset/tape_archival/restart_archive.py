from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.tape_archival.perform_archive_checks import check_archive
from datahubirodsruleset.tape_archival.start_archive import queue_archive


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def restart_archive(ctx, archival_path, username_initiator):
    """Restart a failed archive after its previous execution has stopped.

    Use the original collection path and the tape service account. All ordinary
    archive checks still apply, but archiveState must be error-archive-failed.
    """
    results = check_archive(ctx, archival_path, restart=True)
    queue_archive(ctx, archival_path, username_initiator, results, restart=True)
