"""User listing rules with bulk metadata queries."""
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import in_conditions, query_value


def _user_objects(ctx, rows, condition):
    # Keep the native identity query's order, including users without AVUs.
    users = {}
    for row in rows:
        name, identifier = row[:2]
        users[identifier] = {"userName": name, "userId": identifier, "displayName": name}
    if users:
        for identifier, value in row_iterator(
            "USER_ID, META_USER_ATTR_VALUE", condition + " AND META_USER_ATTR_NAME = 'displayName'", AS_LIST, ctx.callback
        ):
            if identifier in users:
                users[identifier]["displayName"] = value or users[identifier]["userName"]
    return list(users.values())


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_users(ctx, show_service_accounts):
    condition = "USER_TYPE = 'rodsuser'"
    rows = row_iterator("USER_NAME, USER_ID", condition, AS_LIST, ctx.callback)
    users = _user_objects(ctx, rows, condition)
    return [user for user in users if show_service_accounts != "false" or not user["userName"].startswith("service-")]


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_data_stewards(ctx):
    identifiers = [row[0] for row in row_iterator(
        "USER_ID", "META_USER_ATTR_NAME = 'specialty' AND META_USER_ATTR_VALUE = 'data-steward'",
        AS_LIST, ctx.callback,
    )]
    users = []
    for condition in in_conditions("USER_ID", identifiers):
        rows = row_iterator("USER_NAME, USER_ID, META_USER_ATTR_VALUE", condition, AS_LIST, ctx.callback)
        users.extend(_user_objects(ctx, rows, condition))
    return users


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_users_in_group(ctx, group_id):
    condition = f"USER_TYPE = 'rodsuser' AND USER_GROUP_ID = {query_value(group_id)}"
    rows = row_iterator("order(USER_NAME), USER_ID", condition, AS_LIST, ctx.callback)
    return _user_objects(ctx, rows, condition)
