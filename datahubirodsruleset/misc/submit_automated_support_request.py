from datahubirodsruleset.decorator import make, Output

# /rules/tests/run_test.sh -r submit_ingest_error_automated_support_request -a "email@example.org,P000000001,token-token,LOL" -j


@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def submit_ingest_error_automated_support_request(ctx, email, project_id, token, error_message):
    from datetime import datetime

    error_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = (
        "Ingest for dropzone {} (Project {}) has failed, we will contact you when we have more information "
        "available".format(token, project_id)
    )
    ctx.callback.submit_automated_support_request(email, description, error_timestamp, error_message)


@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def submit_automated_support_request(ctx, email, description, error_timestamp, error_message):
    import requests

    # Get the Help Center Backend url
    help_center_backend_base = ctx.callback.get_env("HC_BACKEND_URL", "true", "")["arguments"][2]
    help_center_request_endpoint = "http://{}/help_backend/submit_request/automated_process_support".format(
        help_center_backend_base
    )

    request_json = {
        "email": email,
        "description": description,
        "error_timestamp": error_timestamp,
        "error_message": error_message,
    }
    try:
        response = requests.post(
            help_center_request_endpoint,
            json=request_json,
        )
        if response.ok:
            ctx.callback.msiWriteRodsLog("SUCCESS: TICKET Created '{}'".format(response.status_code), 0)
        else:
            ctx.callback.msiWriteRodsLog("ERROR: Response EpicPID not HTTP OK: '{}'".format(response.status_code), 0)
    except requests.exceptions.RequestException as e:
        ctx.callback.msiWriteRodsLog("Exception while requesting PID: '{}'".format(e), 0)
