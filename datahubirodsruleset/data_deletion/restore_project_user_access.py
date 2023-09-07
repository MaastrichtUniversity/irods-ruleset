# /rules/tests/run_test.sh -r restore_project_user_access -a "/nlmumc/projects/P000000011"
from dhpythonirodsutils.enums import DataDeletionState
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import (
    map_access_name_to_access_level,
    IRODS_BACKUP_ACL_BASE_PATH,
    IRODS_ZONE_BASE_PATH,
    apply_batch_acl_operation,
)
from datahubirodsruleset.data_deletion.restore_project_collection_user_access import (
    remove_collection_deletion_metadata,
    check_collection_delete_data_state,
)
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restore_project_user_access(ctx, user_project_path):
    """
    Restore the current users access from the backup project ACL to the input project ACL
    Additionally:
     * Remove the backup project ACL
     * Remove the "deletion metadata" AVUs

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_path : str
        The absolute path of the project
    """
    backup_project_path = IRODS_BACKUP_ACL_BASE_PATH + user_project_path.replace(IRODS_ZONE_BASE_PATH, "")

    check_collection_delete_data_state(ctx, user_project_path, DataDeletionState.PENDING.value)

    restore_project_user_acl(ctx, user_project_path, backup_project_path)

    ctx.callback.msiRmColl(backup_project_path, "forceFlag=", 0)
    ctx.callback.msiWriteRodsLog("INFO: Deleted backup project '{}'".format(backup_project_path), 0)

    remove_collection_deletion_metadata(ctx, user_project_path)


def restore_project_user_acl(ctx, user_project_path, backup_project_path):
    """
    Transfer the ACL from the backup project to the user project

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_path : str
        The absolute path of the project
    backup_project_path : str
        The absolute path of the backup project ACL
    """
    acl_operations = []
    for result in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE",
        "COLL_NAME = '{}'".format(backup_project_path),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]
        account_access = result[1]
        user_access = map_access_name_to_access_level(account_access)

        for account in row_iterator("USER_NAME", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            acl_operation = {
                "entity_name": account_name,
                "acl": user_access,
            }
            acl_operations.append(acl_operation)

    apply_batch_acl_operation(ctx, user_project_path, acl_operations)
    ctx.callback.msiWriteRodsLog("INFO: Users ACL restored  for '{}'".format(user_project_path), 0)
