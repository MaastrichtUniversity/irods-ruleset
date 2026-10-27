# /rules/tests/run_test.sh -r admin_unlock_direct_dropzone -a "crazy-frog" -j
import re
from subprocess import CalledProcessError, check_call  # nosec: iadmin uses an argument list, never a shell

import irods_types  # pylint: disable=import-error
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def admin_unlock_direct_dropzone(ctx, token):
    """Reset locked replicas to stale in an open or warning-state direct dropzone.

    Only rodsadmin clients may run this recovery, after interrupted uploads have
    stopped. Files and dropzone metadata are preserved. Returns a JSON object
    containing unlocked_replica_count. On failure, earlier updates remain applied;
    rerunning the rule repairs the remaining locked replicas.
    """
    current_user = ctx.callback.get_client_username("")["arguments"][0]
    if current_user != "rods":
        return ctx.callback.msiExit("-1", "Only rodsadmin clients may unlock direct dropzones")

    if not re.fullmatch(r"\w+-\w+", token):
        return ctx.callback.msiExit("-1", f"Invalid dropzone token: {token!r}")
    dropzone_path = formatters.format_dropzone_path(token, "direct")
    ctx.callback.msiObjStat(dropzone_path, irods_types.RodsObjStat())
    state = ctx.callback.getCollectionAVU(dropzone_path, "state", "", "", "true")["arguments"][2]
    if state != "open" and not state.startswith("warning-"):
        return ctx.callback.msiExit("-1", f"Cannot unlock dropzone '{dropzone_path}' in state '{state}'")

    # Query root and descendants separately; filter literally as tokens can contain
    # underscores, which GenQuery LIKE interprets as wildcards.
    replicas = []
    for condition in (f"COLL_NAME = '{dropzone_path}'", f"COLL_NAME LIKE '{dropzone_path}/%'"):
        for collection, name, replica in row_iterator(
            "COLL_NAME, DATA_NAME, DATA_REPL_NUM",
            f"{condition} AND DATA_REPL_STATUS in ('2', '3', '4')",
            AS_LIST,
            ctx.callback,
        ):
            if collection == dropzone_path or collection.startswith(dropzone_path + "/"):
                replicas.append((f"{collection}/{name}", replica))

    unlocked_replica_count = 0
    for path, replica in replicas:
        try:
            check_call(
                ["iadmin", "modrepl", "logical_path", path, "replica_number", replica, "DATA_REPL_STATUS", "0"],
                shell=False,
            )
        except (CalledProcessError, OSError) as err:
            return ctx.callback.msiExit(
                "-1", f"Failed unlocking '{path}' replica {replica} after {unlocked_replica_count} successful updates: {err}"
            )
        unlocked_replica_count += 1
        ctx.callback.msiWriteRodsLog(
            f"INFO: User '{current_user}' reset locked replica '{path}' (repl {replica}) to stale (0)", 0
        )

    return {"unlocked_replica_count": unlocked_replica_count}
