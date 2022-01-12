@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_versioned_pids(ctx, project, collection, version):
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
    pid_requests = []

    # Getting the epicpid url
    epicpid_base = ctx.callback.msi_getenv("EPICPID_URL", "")["arguments"][1]
    ctx.callback.msiWriteRodsLog("Requesting a PID with url {}".format(epicpid_base), 0)

    if version == "0":
        epicpid_root_url = epicpid_base + project + collection
        epicpid_schema_url = epicpid_base + project + collection + "schema"
        epicpid_instance_url = epicpid_base + project + collection + "instance"
    else:
        epicpid_root_url = epicpid_base + project + collection + "." + version
        epicpid_schema_url = epicpid_base + project + collection + "schema" + "." + version
        epicpid_instance_url = epicpid_base + project + collection + "instance" + "." + version

    # Getting the handle URL to format
    mdr_handle_url = ctx.callback.msi_getenv("MDR_HANDLE_URL", "")["arguments"][1]
    if version == "0":
        handle_root_url = mdr_handle_url + project + "/" + collection
        handle_schema_url = mdr_handle_url + project + "/" + collection  + "/" + "schema"
        handle_instance_url = mdr_handle_url + project + "/" + collection  + "/" + "instance"
    else:
        handle_root_url = mdr_handle_url + project + "/" + collection + "." + version
        handle_schema_url = mdr_handle_url + project + "/" + collection + "/" + "schema" + "." + version
        handle_instance_url = mdr_handle_url + project + "/" + collection + "/" + "instance" + "." + version

    pid_requests.append((epicpid_root_url, handle_root_url))
    pid_requests.append((epicpid_schema_url, handle_schema_url))
    pid_requests.append((epicpid_instance_url, handle_instance_url))


    # Getting the epicpid user and password from env variable
    epicpid_user = ctx.callback.msi_getenv("EPICPID_USER", "")["arguments"][1]
    epicpid_password = ctx.callback.msi_getenv("EPICPID_PASSWORD", "")["arguments"][1]

    handle = ""

    for epicpid_url, handle_url in pid_requests:

        ctx.callback.msiWriteRodsLog("Requesting a PID with url {} {}".format(epicpid_url,handle_url), 0)
        # Calling the epicpid microservice
        try:
            response = requests.post(
                epicpid_url,
                json={"URL": handle_url},
                auth=(epicpid_user, epicpid_password),
            )
            response_object = json.loads(response.text)
            handle = str(epicpid_base.split("/")[-2] + "/" + project + collection)
        except requests.exceptions.RequestException as e:
            ctx.callback.msiWriteRodsLog("Exception while requesting PID: '{}'".format(e), 0)
        except KeyError as e:
            ctx.callback.msiWriteRodsLog("KeyError while requesting PID: '{}'".format(e), 0)


    return handle

