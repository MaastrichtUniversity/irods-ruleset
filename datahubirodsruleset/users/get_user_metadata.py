# /rules/tests/run_test.sh -r get_user_metadata -a "jmelius" -j
import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_metadata(ctx, username):
    result = {"username": username}

    ret = ctx.get_user_attribute_value(result["username"], "email", TRUE_AS_STRING, "result")["arguments"][3]
    result["email"] = json.loads(ret)["value"]

    ret = ctx.get_user_attribute_value(result["username"], "displayName", TRUE_AS_STRING, "result")["arguments"][3]
    result["displayName"] = json.loads(ret)["value"]

    split_display_name = result["displayName"].split(" ", 1)
    result["givenName"] = split_display_name[0]
    result["familyName"] = split_display_name[1]

    return result
