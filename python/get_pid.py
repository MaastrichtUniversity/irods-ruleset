@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_pid(ctx, project, collection):
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
    """
    import requests

    # Getting the epicpid url
    epicpid_base = ctx.callback.msi_getenv("EPICPID_URL", "")["arguments"][1]
    ctx.callback.msiWriteRodsLog("Requesting a PID with url {}".format(epicpid_base), 0)
    epicpid_url = epicpid_base + project + collection

    # Getting the handle URL to format
    mdr_handle_url = ctx.callback.msi_getenv("MDR_HANDLE_URL", "")["arguments"][1]
    handle_url = mdr_handle_url + project + "/" + collection

    # Getting the epicpid user and password from env variable
    epicpid_user = ctx.callback.msi_getenv("EPICPID_USER", "")["arguments"][1]
    epicpid_password = ctx.callback.msi_getenv("EPICPID_PASSWORD", "")["arguments"][1]

    handle = ""

    # Calling the epicpid microservice
    try:
        response = requests.post(
            epicpid_url,
            json={"URL": handle_url},
            auth=(epicpid_user, epicpid_password),
        )
        response_object = json.loads(response.text)
        handle = response_object["handle"]
    except requests.exceptions.RequestException as e:
        ctx.callback.msiWriteRodsLog("Exception while requesting PID: '{}'".format(e), 0)
    except KeyError as e:
        ctx.callback.msiWriteRodsLog("KeyError while requesting PID: '{}'".format(e), 0)

    return str(handle)
