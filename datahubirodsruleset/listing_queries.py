"""Bulk catalog reads shared by listing rules, using the caller's permissions."""
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error


def query_value(value):
    return "'" + str(value).replace("'", "''") + "'"


def in_conditions(column, values):
    # Leave room for the attribute/access filters appended by callers. Both
    # names and 19-digit catalog IDs must fit GenQuery's condition buffer.
    batch = []
    for value in dict.fromkeys(values):
        literal = query_value(value)
        if batch and (len(batch) == 20 or len(",".join(batch).encode("utf-8")) + len(literal.encode("utf-8")) > 600):
            yield f"{column} in ({','.join(batch)})"
            batch = []
        batch.append(literal)
    if batch:
        yield f"{column} in ({','.join(batch)})"


def collection_metadata(ctx, condition, attributes=()):
    if attributes:
        condition += " AND META_COLL_ATTR_NAME in (" + ",".join(map(query_value, attributes)) + ")"
    metadata = {}
    for path, attribute, value in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE", condition, AS_LIST, ctx.callback
    ):
        metadata.setdefault(path, {})[attribute] = value
    return metadata


def metadata_for_paths(ctx, paths, attributes):
    metadata = {}
    for condition in in_conditions("COLL_NAME", paths):
        metadata.update(collection_metadata(ctx, condition, attributes))
    return metadata


def avu(ctx, metadata, path, attribute, default="", fatal=False):
    value = metadata.get(path, {}).get(attribute, "")
    if value == "":
        if fatal:
            ctx.callback.msiExit(
                "-1", f"ERROR: The attribute '{attribute}' of collection '{path}' has no value in iCAT"
            )
        return default
    return value


def account_identities(ctx, identifiers):
    result = {}
    for condition in in_conditions("USER_ID", identifiers):
        for account_id, name, account_type in row_iterator(
            "USER_ID, USER_NAME, USER_TYPE", condition, AS_LIST, ctx.callback
        ):
            result[account_id] = (name, account_type)
    return result


def accounts(ctx, condition):
    result = {}
    for name, account_id, account_type in row_iterator(
        "order(USER_NAME), USER_ID, USER_TYPE", condition, AS_LIST, ctx.callback
    ):
        result[account_id] = {"name": name, "type": account_type, "displayName": name, "description": ""}
    if result:
        for account_id, attribute, value in row_iterator(
            "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
            condition + " AND META_USER_ATTR_NAME in ('displayName','description')",
            AS_LIST,
            ctx.callback,
        ):
            if account_id in result:
                result[account_id][attribute] = value
    return result


def _project_accounts(ctx, path, levels, show_service_accounts):
    entries = list(row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME",
        f"COLL_NAME = {query_value(path)} AND COLL_ACCESS_NAME in ({','.join(map(query_value, levels))})",
        AS_LIST,
        ctx.callback,
    ))
    resolved = {}
    for condition in in_conditions("USER_ID", (entry[0] for entry in entries)):
        resolved.update(accounts(ctx, condition))
    resolved = {
        identifier: account for identifier, account in resolved.items()
        if account["type"] == "rodsgroup" or (
            account["type"] == "rodsuser" and (show_service_accounts or "service-" not in account["name"])
        )
    }
    return entries, resolved


def _role(entries, resolved):
    result = {"users": [], "groups": [], "groupObjects": [], "userObjects": []}
    for account_id, _ in entries:
        account = resolved.get(account_id)
        if account is None:
            continue
        if account["type"] == "rodsgroup":
            result["groups"].append(account["name"])
            result["groupObjects"].append({
                "groupName": account["name"], "groupId": account_id,
                "displayName": account["displayName"], "description": account["description"],
            })
        else:
            result["users"].append(account["name"])
            result["userObjects"].append({
                "userName": account["name"], "userId": account_id, "displayName": account["displayName"],
            })
    return result


def project_acl(ctx, path, levels, show_service_accounts):
    entries, resolved = _project_accounts(ctx, path, levels, show_service_accounts)
    return _role(entries, resolved)


def project_roles(ctx, path, show_service_accounts):
    levels = ("own", "modify_object", "read_object")
    entries, resolved = _project_accounts(ctx, path, levels, show_service_accounts)
    return {level: _role((entry for entry in entries if entry[1] == level), resolved) for level in levels}
