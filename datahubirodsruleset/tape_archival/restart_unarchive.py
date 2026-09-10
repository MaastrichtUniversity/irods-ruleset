# Resume the stored file or collection scope using the project collection path:
# /rules/tests/run_test.sh -r restart_unarchive -a "/nlmumc/projects/P000000017/C000000001" -u service-surfarchive
# Older failures without unArchivePath restart the entire project collection.
from posixpath import normpath

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.tape_archival.perform_unarchive_checks import check_unarchive
from datahubirodsruleset.tape_archival.start_unarchive import queue_unarchive
from datahubirodsruleset.utils import FALSE_AS_STRING


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restart_unarchive(ctx, unarchival_path):
    """Restart a failed unarchive after its previous execution has stopped.

    Use the project collection path and the tape service account. The stored
    unArchivePath determines the scope, taking precedence over the supplied path.
    If absent, the entire project collection is unarchived, even for a file input.
    All ordinary checks apply, but unArchiveState must be error-unarchive-failed.
    The tape service account is also used as the initiator.
    """
    results = check_unarchive(ctx, unarchival_path, restart=True)
    project_collection_path = results["project_collection_path"]
    unarchival_path = ctx.callback.getCollectionAVU(
        project_collection_path, "unArchivePath", "", project_collection_path, FALSE_AS_STRING
    )["arguments"][2]
    normalized_path = normpath(unarchival_path)
    if normalized_path != project_collection_path and not normalized_path.startswith(f"{project_collection_path}/"):
        ctx.callback.msiExit("-1", f"Stored unArchivePath is outside project collection: '{unarchival_path}'")
        return
    queue_unarchive(ctx, unarchival_path, results["service_account"], results, restart=True)
