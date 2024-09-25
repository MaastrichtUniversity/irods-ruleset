# /rules/tests/run_test.sh -r start_archive -a "/nlmumc/projects/P000000017/C000000001,dlinssen" -u service-surfarchive
import json

from datahubirodsruleset.decorator import make, Output
from dhpythonirodsutils.enums import ProcessAttribute, ArchiveState


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def start_archive(ctx, archival_path, username_initiator):
    """
    Start the archival flow for a project collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    archival_path: str
        The full path of the collection to be archived, e.g. '/nlmumc/projects/P000000017/C000000001'
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    """
    results = json.loads(ctx.callback.perform_archive_checks(archival_path, username_initiator, "")["arguments"][1])

    # Log statements
    ctx.callback.msiWriteRodsLog("INFO: Archival workflow started for {}".format(archival_path), 0)
    ctx.callback.msiWriteRodsLog(
        "DEBUG: Data will be moved onto resource {}".format(results["tape_resource"]), 0
    )
    ctx.callback.msiWriteRodsLog("DEBUG: Service account used is {}".format(results["service_account"]), 0)
    ctx.callback.msiWriteRodsLog("DEBUG: {} is the initiator".format(username_initiator), 0)

    # Open the PC up for the service account (which should be an admin)
    ctx.callback.msiSetACL("recursive", "admin:own", results["service_account"], results["project_collection_path"])

    # Set the tape AVU so the user sees the active process even if it has not started yet
    ctx.callback.setCollectionAVU(
        results["project_collection_path"], ProcessAttribute.ARCHIVE.value, ArchiveState.IN_QUEUE_FOR_ARCHIVAL.value
    )

    # Perform the rest of the steps in the Delay queue, as to not lock up the user until it finished
    ctx.delayExec(
        "<PLUSET>1s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        "perform_archive('{}', '{}', '{}')".format(archival_path, json.dumps(results), username_initiator),
        "",
    )
