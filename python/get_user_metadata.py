@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_metadata(ctx, username):
    result = {"username": username}

    ret = ctx.get_username_attribute_value(result["username"], "email", "result")["arguments"][2]
    result["email"] = json.loads(ret)["value"]

    ret = ctx.get_username_attribute_value(result["username"], "displayName", "result")["arguments"][2]
    result["displayName"] = json.loads(ret)["value"]

    split_display_name = result["displayName"].split(" ", 1)
    result["givenName"] = split_display_name[0]
    result["familyName"] = split_display_name[1]

    return result
