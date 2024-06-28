# Part of the archival flow. Not to be called by user
import json

from dhpythonirodsutils.enums import ProcessAttribute

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def perform_unarchive_recursion(ctx, unarchival_path, check_results, username_initiator):
    """
    This rule is recursively called every 30s in the unarchival flow to wait for all the files
    to be staged back online.
    Once all files are staged 'online' (no files in 'OFL' or 'UNM' state), the process for replication
    will begin.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    unarchival_path: str
        The full path of the collection OR file to be unarchived, e.g. '/nlmumc/projects/P000000017/C000000001' or '/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log'
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    """
    check_results = json.loads(check_results)
    dm_attr_output = json.loads(
        ctx.callback.dm_attr(
            unarchival_path, check_results["archive_destination_resource"], check_results["resource_location"], ""
        )["arguments"][3]
    )

    return_value = {
        "project_id": check_results["project_id"],
        "project_collection_id": check_results["project_collection_id"],
        "project_collection_path": check_results["project_collection_path"],
        "resource_location": check_results["resource_location"],
        "service_account": check_results["service_account"],
        "archive_destination_resource": check_results["archive_destination_resource"],
        "unarchival_path": unarchival_path,
    }

    log_message = "msiWriteRodsLog('DEBUG: SURFSara Archive - delay 30s, before retry', 0)"
    rule_call = "perform_unarchive_recursion('{}', '{}', '')".format(unarchival_path, json.dumps(check_results))
    recurse = "{};{}".format(log_message, rule_call)

    if dm_attr_output["files_offline"]:
        ctx.callback.setCollectionAVU(
            check_results["project_collection_path"],
            ProcessAttribute.UNARCHIVE.value,
            "Number of files offline: {}".format(str(dm_attr_output["count"])),
        )
        for file_offline in dm_attr_output["files_offline"]:
            ctx.callback.dmget(file_offline["physical_path"], check_results["resource_location"])
        ctx.delayExec(
            "<PLUSET>30s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            recurse,
            "",
        )
        return

    if dm_attr_output["files_unmigrating"]:
        ctx.callback.setCollectionAVU(
            check_results["project_collection_path"],
            ProcessAttribute.UNARCHIVE.value,
            "Caching files countdown: {}".format(len(dm_attr_output["files_unmigrating"])),
        )
        ctx.delayExec(
            "<PLUSET>30s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
            recurse,
            "",
        )
        return

    else:
        if dm_attr_output["files_online"]:
            ctx.callback.setCollectionAVU(
                check_results["project_collection_path"], ProcessAttribute.UNARCHIVE.value, "start-transfer"
            )
            ctx.callback.perform_unarchive(json.dumps(return_value), username_initiator)
        else:
            ctx.callback.msiWriteRodsLog("DEBUG: Nothing to un-archive", 0)
