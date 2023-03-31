# /rules/tests/run_test.sh -r get_versioned_pids -a "P000000014,C000000001,2" -u jmelius -j
import json
import time

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_collection_path


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_versioned_pids(ctx, project_id, collection_id, version=None):
    """
    Request a PID via EpicPID

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project to request and set a pid for (e.g: P000000010)
    collection_id : str
        The collection to request and set a PID for (e.g: C000000002)
    version : str
        The version number of collection,schema and instance that PID are requested for
    """
    import requests

    # Getting the EpicPID url
    epicpid_base = ctx.callback.get_env("EPICPID_URL", "true", "")["arguments"][2]
    ctx.callback.msiWriteRodsLog(
        "Requesting multiple PID's with base url: {} project: {} collection: {} version: {}".format(
            epicpid_base, project_id, collection_id, version
        ),
        0,
    )
    epicpid_url = epicpid_base + "multiple/" + project_id + collection_id

    # Getting the handle URL to format
    mdr_handle_url = ctx.callback.get_env("MDR_HANDLE_URL", "true", "")["arguments"][2]
    handle_url = mdr_handle_url + project_id + "/" + collection_id

    # Getting the EpicPID user and password from env variable
    epicpid_user = ctx.callback.get_env("EPICPID_USER", "true", "")["arguments"][2]
    epicpid_password = ctx.callback.get_env("EPICPID_PASSWORD", "true", "")["arguments"][2]

    handle = {}

    request_json = {"URL": handle_url}
    if version:
        request_json["VERSION"] = version

    # Add simple retry retrieving PID
    RETRY_MAX_NUMBER = 5
    RETRY_SLEEP_NUMBER = 30
    retry_counter = RETRY_MAX_NUMBER
    return_code = 0

    while retry_counter > 0:
        try:
            response = requests.post(
                epicpid_url,
                json=request_json,
                auth=(epicpid_user, epicpid_password),
            )
            if response.ok:
                handle = json.loads(response.text)
                return_code = 0
            else:
                ctx.callback.msiWriteRodsLog("ERROR: Response EpicPID not HTTP OK: '{}'".format(response.status_code), 0)
                return_code = 1

        except requests.exceptions.RequestException as e:
            ctx.callback.msiWriteRodsLog("Exception while requesting PID: '{}'".format(e), 0)
            return_code = 1
        except KeyError as e:
            ctx.callback.msiWriteRodsLog("KeyError while requesting PID: '{}'".format(e), 0)
            return_code = 1

        destination_project_collection_path = format_project_collection_path(ctx, project_id, collection_id)
        if not handle:
            ctx.callback.msiWriteRodsLog(
                "Retrieving multiple PID's failed for {}, leaving blank".format(destination_project_collection_path), 0
            )
            return_code = 1
        if "collection" not in handle or handle["collection"]["handle"] == "":
            ctx.callback.msiWriteRodsLog(
                "Retrieving PID for root collection failed for {}, leaving blank".format(
                    destination_project_collection_path
                ),
                0,
            )
            return_code = 1
        if "schema" not in handle or handle["schema"]["handle"] == "":
            ctx.callback.msiWriteRodsLog(
                "Retrieving PID for root collection schema failed for {}, leaving blank".format(
                    destination_project_collection_path
                ),
                0,
            )
            return_code = 1
        if "instance" not in handle or handle["instance"]["handle"] == "":
            ctx.callback.msiWriteRodsLog(
                "Retrieving PID for root collection instance failed for {}, leaving blank".format(
                    destination_project_collection_path
                ),
                0,
            )
            return_code = 1

        if return_code != 0:
            retry_counter -= 1
            ctx.callback.msiWriteRodsLog("DEBUG: Decrement retry_counter: {}".format(str(retry_counter)), 0)
            time.sleep(RETRY_SLEEP_NUMBER)
        else:
            retry_counter = 0
            ctx.callback.msiWriteRodsLog("INFO: Retrieving PID was successful", 0)
            return handle

    if return_code != 0:
        ctx.callback.msiWriteRodsLog("ERROR: Requesting PID, max retries exceeded", 0)
        return handle
