from datahubirodsruleset import FALSE_AS_STRING, TRUE_AS_STRING
from datahubirodsruleset.decorator import make, Output

# /rules/tests/run_test.sh -r submit_ingest_error_automated_support_request -a "jmelius,P000000001,token-token,LOL" -j
# /rules/tests/run_test.sh -r submit_automated_support_request -a "email@example.org,description,error" -j


@make(inputs=[0, 1, 2, 3], outputs=[4], handler=Output.STORE)
def submit_ingest_error_automated_support_request(ctx, username, project_id, token, error_message):
    import json

    ret = ctx.get_user_attribute_value(username, "email", FALSE_AS_STRING, "result")["arguments"][3]
    email = json.loads(ret)["value"]

    description = (
        "Ingest for dropzone {} (Project {}) has failed, we will contact you when we have more information "
        "available".format(token, project_id)
    )
    issue_key = ctx.callback.submit_automated_support_request(email, description, error_message, "")["arguments"][3]
    return issue_key


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def submit_automated_support_request(ctx, email, description, error_message):
    import requests
    from datetime import datetime

    # Get the Help Center Backend url
    help_center_backend_base = ctx.callback.get_env("HC_BACKEND_URL", TRUE_AS_STRING, "")["arguments"][2]
    help_center_request_endpoint = "{}/help_backend/submit_request/automated_process_support".format(
        help_center_backend_base
    )

    error_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    request_json = {
        "email": email,
        "description": description,
        "error_timestamp": error_timestamp,
        "error_message": error_message,
    }
    issue_key = ""
    try:
        response = requests.post(
            help_center_request_endpoint,
            json=request_json,
        )
        if response.ok:
            issue_key = response.json()["issueKey"]
            ctx.callback.msiWriteRodsLog("Support ticket '{}' created after process error".format(issue_key), 0)

        else:
            ctx.callback.msiWriteRodsLog(
                "ERROR: Response Help center backend not HTTP OK: '{}'".format(response.status_code), 0
            )
    except requests.exceptions.RequestException as e:
        ctx.callback.msiWriteRodsLog(
            "ERROR: Exception while requesting Support ticket after process error '{}'".format(e), 0
        )

    return issue_key
