# Entire collection:
# /rules/tests/run_test.sh -r start_unarchive -a "/nlmumc/projects/P000000017/C000000001,dlinssen" -u service-surfarchive
# Single file:
# /rules/tests/run_test.sh -r start_unarchive -a "/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log,dlinssen" -u service-surfarchive
import json

from datahubirodsruleset.decorator import make, Output
from dhpythonirodsutils.enums import ProcessAttribute, UnarchiveState


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def start_unarchive(ctx, unarchival_path, username_initiator):
    """
    Start the unarchival flow for a project collection or file in a project collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    unarchival_path: str
        The full path of the collection OR file to be unarchived, e.g. '/nlmumc/projects/P000000017/C000000001' or '/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log'
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    """
    results = json.loads(ctx.callback.perform_unarchive_checks(unarchival_path, "")["arguments"][1])

    # Log statements
    ctx.callback.msiWriteRodsLog("INFO: UnArchival workflow started for {}".format(unarchival_path), 0)
    ctx.callback.msiWriteRodsLog(
        "DEBUG: Data will be moved from resource {}".format(results["archive_destination_resource"]), 0
    )
    ctx.callback.msiWriteRodsLog("DEBUG: Service account used is {}".format(results["service_account"]), 0)
    ctx.callback.msiWriteRodsLog("DEBUG: {} is the initiator".format(username_initiator), 0)

    # Open the PC up for the service account (which should be an admin)
    ctx.callback.msiSetACL("recursive", "admin:own", results["service_account"], results["project_collection_path"])

    # Set the tape AVU so the user sees the active process even if it has not started yet
    ctx.callback.setCollectionAVU(
        results["project_collection_path"], ProcessAttribute.UNARCHIVE.value, UnarchiveState.IN_QUEUE_FOR_UNARCHIVAL.value
    )

    # Perform the rest of the steps in the Delay queue, as to not lock up the user until it finished
    ctx.delayExec(
        "<PLUSET>1s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        "perform_unarchive_recursion('{}', '{}', '{}')".format(
            unarchival_path, json.dumps(results), username_initiator
        ),
        "",
    )
