# /rules/tests/run_test.sh -r restore_project_access -a "/nlmumc/projects/P000000011"
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restore_project_access(ctx, user_project):
    backup_project = "/nlmumc/trash" + user_project.replace("/nlmumc", "")

    for result in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE",
        "COLL_NAME = '{}'".format(backup_project),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]
        account_access = result[1]
        user_access = convert_acl_to_access_right(account_access)

        for account in row_iterator("USER_NAME", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            ctx.callback.msiSetACL("default", user_access, account_name, user_project)

    ctx.callback.msiWriteRodsLog("Users ACL restored  for '{}'".format(user_project), 0)

    ctx.callback.msiRmColl(backup_project, "forceFlag=", 0)
    ctx.callback.msiWriteRodsLog("Deleted backup project '{}'".format(backup_project), 0)

    # TODO Remove 'deletion metadata' AVUs


def convert_acl_to_access_right(account_access):
    user_access = account_access
    if account_access == "modify object":
        user_access = "write"
    elif account_access == "read object":
        user_access = "read"

    return user_access
