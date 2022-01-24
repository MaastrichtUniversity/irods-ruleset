@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_versioned_pids(ctx, project, collection, version=None):
    """
    Request a PID via epicpid

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project : str
        The project to request and set a pid for (ie. P000000010)
    collection : str
        The collection to request and set a PID for (ie. C000000002)
    version : str
        The version number of collection,schema and instance that PID are requested for
    """
    import requests

    # Getting the epicpid url
    epicpid_base = ctx.callback.msi_getenv("EPICPID_URL", "")["arguments"][1]
    ctx.callback.msiWriteRodsLog(
        "Requesting multiple PID's with base url: {} project: {} collection: {} version: {}".format(
            epicpid_base, project, collection, version
        ),
        0,
    )
    epicpid_url = epicpid_base + "multiple/" + project + collection

    # Getting the handle URL to format
    mdr_handle_url = ctx.callback.msi_getenv("MDR_HANDLE_URL", "")["arguments"][1]
    handle_url = mdr_handle_url + project + "/" + collection

    # Getting the epicpid user and password from env variable
    epicpid_user = ctx.callback.msi_getenv("EPICPID_USER", "")["arguments"][1]
    epicpid_password = ctx.callback.msi_getenv("EPICPID_PASSWORD", "")["arguments"][1]

    handle = {}
    if version:
        try:
            response = requests.post(
                epicpid_url,
                json={"URL": handle_url, "VERSION": version},
                auth=(epicpid_user, epicpid_password),
            )
            handle = json.loads(response.text)
        except requests.exceptions.RequestException as e:
            ctx.callback.msiWriteRodsLog("Exception while requesting PID: '{}'".format(e), 0)
        except KeyError as e:
            ctx.callback.msiWriteRodsLog("KeyError while requesting PID: '{}'".format(e), 0)
    else:
        try:
            response = requests.post(
                epicpid_url,
                json={"URL": handle_url},
                auth=(epicpid_user, epicpid_password),
            )
            handle = json.loads(response.text)
        except requests.exceptions.RequestException as e:
            ctx.callback.msiWriteRodsLog("Exception while requesting PID: '{}'".format(e), 0)
        except KeyError as e:
            ctx.callback.msiWriteRodsLog("KeyError while requesting PID: '{}'".format(e), 0)

    return handle
