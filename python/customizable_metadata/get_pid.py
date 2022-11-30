@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_pid(ctx, project_id, collection_id):
    """
    Request a PID via epicpid

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    project_id : str
        The project to request and set a pid for (ie. P000000010)
    collection_id : str
        The collection to request and set a PID for (ie. C000000002)
    """
    import requests

    # Getting the epicpid url
    epicpid_base = ctx.callback.get_env("EPICPID_URL", "true", "")["arguments"][2]
    ctx.callback.msiWriteRodsLog("Requesting a PID with url {}".format(epicpid_base), 0)
    epicpid_url = epicpid_base + "single/" + project_id + collection_id

    # Getting the handle URL to format
    mdr_handle_url = ctx.callback.get_env("MDR_HANDLE_URL", "true", "")["arguments"][2]
    handle_url = mdr_handle_url + project_id + "/" + collection_id

    # Getting the epicpid user and password from env variable
    epicpid_user = ctx.callback.get_env("EPICPID_USER", "true", "")["arguments"][2]
    epicpid_password = ctx.callback.get_env("EPICPID_PASSWORD", "true", "")["arguments"][2]

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
