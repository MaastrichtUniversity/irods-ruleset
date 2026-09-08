from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.tape_archival.perform_unarchive_checks import check_unarchive
from datahubirodsruleset.tape_archival.start_unarchive import queue_unarchive


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def restart_unarchive(ctx, unarchival_path, username_initiator):
    """Restart a failed unarchive after its previous execution has stopped.

    Use the original collection or file path and the tape service account. All
    ordinary checks still apply, but unArchiveState must be error-unarchive-failed.
    """
    results = check_unarchive(ctx, unarchival_path, restart=True)
    queue_unarchive(ctx, unarchival_path, username_initiator, results, restart=True)
