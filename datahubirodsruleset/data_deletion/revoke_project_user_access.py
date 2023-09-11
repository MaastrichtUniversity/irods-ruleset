# /rules/tests/run_test.sh -r revoke_project_user_access -a "/nlmumc/projects/P000000011,funding_expired,description24"
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionAttribute, DataDeletionState
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import IRODS_BACKUP_ACL_BASE_PATH, IRODS_ZONE_BASE_PATH
from datahubirodsruleset.data_deletion.restore_project_user_access import map_access_name_to_access_level
from datahubirodsruleset.data_deletion.revoke_project_collection_user_access import apply_collection_deletion_metadata
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.projects.get_project_process_activity import (
    check_active_dropzone_by_project_id,
    check_pending_deletions_by_project_id,
    check_project_process_activity,
)


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def revoke_project_user_access(ctx, user_project, reason, description):
    """
    After a user request a project deletion, all users accesses need to be revoked immediately. Including all
    collections that have not yet been deleted.
    Additionally:
     * Check if there are any ongoing process linked to the project, this includes dropzones and pending deletions.
      If true, stop the rule execution
     * The 'deletion metadata' need to be set as AVUs on the project
     * Backup of ACL is created

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project : str
         The absolute path of the project
    reason : str
        The reason of the deletion
    description : str
        An optional description providing additional details, empty string if not provided by the form/user
    """
    project_id = formatters.get_project_id_from_project_path(user_project)
    has_active_drop_zones = check_active_dropzone_by_project_id(ctx, project_id)
    has_active_processes = check_project_process_activity(ctx, project_id)
    has_pending_deletions = check_pending_deletions_by_project_id(ctx, project_id)

    if has_active_drop_zones or has_active_processes or has_pending_deletions:
        ctx.callback.msiExit("-1", "Stop execution, active proces(ses) found for project {}".format(user_project))
        return

    backup_project = IRODS_BACKUP_ACL_BASE_PATH + user_project.replace(IRODS_ZONE_BASE_PATH, "")
    try:
        ctx.callback.msiCollCreate(backup_project, 1, 0)
    except RuntimeError:
        ctx.callback.msiWriteRodsLog("ERROR: Could not create backup project '{}'".format(backup_project), 0)
        ctx.callback.msiExit("-1", "Stop execution, could not create backup project '{}'".format(backup_project))
        return

    apply_collection_deletion_metadata(ctx, user_project, reason, description, "add")
    ctx.callback.msiWriteRodsLog("INFO: Create ACL backup for project '{}'".format(backup_project), 0)

    for result in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE",
        "COLL_NAME = '{}'".format(user_project),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]
        account_access = result[1]
        user_access = map_access_name_to_access_level(account_access)

        for account in row_iterator("USER_NAME, USER_TYPE", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            account_type = account[1]
            ctx.callback.msiSetACL("default", user_access, account_name, backup_project)

            if account_type != "rodsadmin" and "service-" not in account_name:
                ctx.callback.msiSetACL("default", "null", account_name, user_project)

    ctx.callback.msiWriteRodsLog("INFO: Users ACL revoked for project '{}'".format(user_project), 0)

    ctx.callback.msiWriteRodsLog("INFO: Revoke users ACL for collections in project '{}'".format(user_project), 0)
    for proj_coll in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '{}'".format(user_project), AS_LIST, ctx.callback):
        project_collection_path = proj_coll[0]
        # For already deleted collections we do not revoke anything, this is already done
        output = ctx.callback.get_collection_attribute_value(
            project_collection_path, DataDeletionAttribute.STATE.value, "result"
        )["arguments"][2]
        data_deletion_status = json.loads(output)["value"]
        if data_deletion_status == DataDeletionState.DELETED.value:
            continue

        ctx.revoke_project_collection_user_access(project_collection_path, reason, description)
