# /rules/tests/run_test.sh -r revoke_project_user_access -a "/nlmumc/projects/P000000011"
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProcessAttribute
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import IRODS_BACKUP_ACL_BASE_PATH, IRODS_ZONE_BASE_PATH
from datahubirodsruleset.data_deletion.restore_project_user_access import map_access_name_to_access_level
from datahubirodsruleset.decorator import make, Output

# TODO - POC rule
#   Refactor this rule during DHS-3024


@make(inputs=[0], outputs=[], handler=Output.STORE)
def revoke_project_user_access(ctx, user_project):
    project_id = formatters.get_project_id_from_project_path(user_project)
    has_active_drop_zones = check_active_dropzone_by_project_id(ctx, project_id)
    has_active_processes = check_active_processes_by_project_id(ctx, project_id)

    if has_active_drop_zones or has_active_processes:
        ctx.callback.msiExit("-1", "Stop execution, active proces(ses) found for project {}".format(user_project))
        return

    backup_project = IRODS_BACKUP_ACL_BASE_PATH + user_project.replace(IRODS_ZONE_BASE_PATH, "")
    try:
        ctx.callback.msiCollCreate(backup_project, 1, 0)
    except RuntimeError:
        print("ERROR: msiCollCreate")

    ctx.callback.msiWriteRodsLog("INFO: Create ACL backup for project '{}'".format(backup_project), 0)
    apply_batch_collection_avu_operation(ctx, user_project, "add")

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
        ctx.revoke_project_collection_user_access(proj_coll[0], "deletionReason", "deletionReasonDescription")


def check_active_dropzone_by_project_id(ctx, project_id):
    parameters = "COLL_NAME, META_COLL_ATTR_VALUE"
    conditions = (
        "COLL_PARENT_NAME in ('/nlmumc/ingest/zones','/nlmumc/ingest/direct') "
        "AND META_COLL_ATTR_NAME = 'project' "
        "AND META_COLL_ATTR_VALUE = '{}'".format(project_id)
    )
    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        token = result[0]
        dropzone_project_id = result[1]
        print("{} -> {}".format(token, dropzone_project_id))
        return True

    return False


def check_active_processes_by_project_id(ctx, project_id):
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}', '{}') AND COLL_PARENT_NAME LIKE '/nlmumc/projects/{}' ".format(
        ProcessAttribute.ARCHIVE.value,
        ProcessAttribute.UNARCHIVE.value,
        ProcessAttribute.EXPORTER.value,
        project_id,
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        name = result[0]
        process = result[1]
        print("{} -> {}".format(name, process))
        return True

    return False


def apply_batch_collection_avu_operation(ctx, collection, operation):
    json_input = {
        "entity_name": collection,
        "entity_type": "collection",
        "operations": [
            {
                "operation": operation,
                "attribute": "deletionReason",
                "value": "deletionReason",
            },
            {
                "operation": operation,
                "attribute": "deletionReasonDescription",
                "value": "deletionReasonDescription",
            },
            {
                "operation": operation,
                "attribute": "deletionState",
                "value": "pending-for-deletion",
            },
        ],
    }
    str_json_input = json.dumps(json_input)
    ctx.msi_atomic_apply_metadata_operations(str_json_input, "")
    message = "INFO: {} deletion metadata for {}".format(operation, collection)
    ctx.callback.msiWriteRodsLog(message, 0)
