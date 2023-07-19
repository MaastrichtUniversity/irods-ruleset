# /rules/tests/run_test.sh -r revoke_project_collection_access -a "/nlmumc/projects/P000000002/C000000001"
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def revoke_project_collection_access(ctx, user_project_collection):

    for result in row_iterator(
        "COLL_ACCESS_USER_ID",
        "COLL_NAME = '{}'".format(user_project_collection),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]

        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            account_type = account[1]

            if account_type != "rodsadmin" and "service-" not in account_name:
                ctx.callback.msiSetACL("recursive", "admin:null", account_name, user_project_collection)

    ctx.callback.msiWriteRodsLog("Users ACL revoked  for '{}'".format(user_project_collection), 0)
    ctx.callback.msiSetACL("recursive", "admin:read", "rods", user_project_collection)
