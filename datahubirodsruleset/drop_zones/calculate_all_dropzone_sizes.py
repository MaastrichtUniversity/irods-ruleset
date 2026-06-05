# To add in the iRODS delay queue (recommended, it could take a while)
# /rules/tests/run_test.sh -r calculate_all_dropzone_sizes_delay
# To run it immediately (not recommended)
# /rules/tests/run_test.sh -r calculate_all_dropzone_sizes
import json
from datetime import datetime, timezone

from dhpythonirodsutils.enums import ProjectAVUs
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING, FALSE_AS_STRING
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error


RULE_ENGINE_INSTANCE = "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>"
CURRENT_TIMESTAMP = str(int(datetime.now().timestamp()))


def _calculate_direct_dropzone_size(ctx, token):
    """Calculate and store size for a direct dropzone."""
    dropzone_path = f"/nlmumc/ingest/direct/{token}"
    size = ctx.callback.calcCollectionSize(dropzone_path, "B", "ceiling", "")["arguments"][3]
    
    ctx.callback.msiWriteRodsLog(f"Size of direct dropzone with token {token}: {size}B", 0)
    ctx.callback.msiSetACL("default", "admin:own", "rods", dropzone_path)
    ctx.callback.setCollectionAVU(dropzone_path, "dropzoneSize", size)
    ctx.callback.setCollectionAVU(dropzone_path, "dropzoneSizeUpdated", CURRENT_TIMESTAMP)
    ctx.callback.msiSetACL("default", "null", "rods", dropzone_path)


def _get_ingest_resource_host(ctx, resource_name):
    """Get the host for a given resource name."""
    for row in row_iterator("RESC_LOC", f"RESC_NAME = '{resource_name}'", AS_LIST, ctx.callback):
        return row[0]


def _process_mounted_dropzones(ctx, dropzones):
    """Process mounted dropzones for a specific resource type (UM or AZM)."""
    if not dropzones:
        return

    ingest_resource = ctx.callback.getCollectionAVU(
        format_project_path(ctx, dropzones[0]["project"]),
        ProjectAVUs.INGEST_RESOURCE.value,
        "",
        "",
        TRUE_AS_STRING,
    )["arguments"][2]

    ingest_resource_host = _get_ingest_resource_host(ctx, ingest_resource)
    tokens = [dropzone["token"] for dropzone in dropzones]

    ctx.remoteExec(
        ingest_resource_host,
        RULE_ENGINE_INSTANCE,
        f"calculate_mounted_dropzone_sizes('{json.dumps(tokens)}')",
        "",
    )

@make(inputs=[], outputs=[], handler=Output.STORE)
def calculate_all_dropzone_sizes(ctx):
    """
    Calculate the total size of all files in all currently 'open' dropzones.
    Internal implementation rule.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    """
    active_dropzones = json.loads(
        ctx.callback.admin_get_user_active_processes(
            TRUE_AS_STRING, FALSE_AS_STRING, FALSE_AS_STRING, ""
        )["arguments"][3]
    )

    if not active_dropzones["open"]:
        ctx.callback.msiWriteRodsLog("No open dropzones found, skipping size calculation", 0)
        return

    um_dropzones = []
    azm_dropzones = []

    for dropzone in active_dropzones["open"]:
        if dropzone["type"] == "direct":
            _calculate_direct_dropzone_size(ctx, dropzone["token"])
        elif dropzone["type"] == "mounted":
            if "AZM" in dropzone["destination_resource"]:
                azm_dropzones.append(dropzone)
            elif "UM" in dropzone["destination_resource"]:
                um_dropzones.append(dropzone)

    _process_mounted_dropzones(ctx, um_dropzones)
    _process_mounted_dropzones(ctx, azm_dropzones)


@make(inputs=[], outputs=[], handler=Output.STORE)
def calculate_all_dropzone_sizes_delay(ctx):
    """
    Calculate the total size of all files in all currently 'open' dropzones.
    This is a public admin rule that schedules the actual processing in the delay queue.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    """
    ctx.callback.delayExec("<PLUSET>1s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
                            "calculate_all_dropzone_sizes()", 
                            "")
            