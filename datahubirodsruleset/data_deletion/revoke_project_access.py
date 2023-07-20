# /rules/tests/run_test.sh -r revoke_project_access -a "/nlmumc/projects/P000000011"
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.data_deletion.restore_project_access import convert_acl_to_access_right
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def revoke_project_access(ctx, user_project):
    backup_project = "/nlmumc/trash" + user_project.replace("/nlmumc", "")

    # TODO Set 'deletion metadata' AVUs
    try:
        ctx.callback.msiCollCreate(backup_project, 1, 0)
    except RuntimeError:
        print("ERROR: msiCollCreate")

    ctx.callback.msiWriteRodsLog("Backup project ACL created '{}'".format(backup_project), 0)

    for result in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE",
        "COLL_NAME = '{}'".format(user_project),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]
        account_access = result[1]
        user_access = convert_acl_to_access_right(account_access)

        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            account_type = account[1]
            ctx.callback.msiSetACL("default", user_access, account_name, backup_project)

            if account_type != "rodsadmin" and "service-" not in account_name:
                ctx.callback.msiSetACL("default", "null", account_name, user_project)

    ctx.callback.msiWriteRodsLog("Users ACL revoked  for '{}'".format(user_project), 0)
