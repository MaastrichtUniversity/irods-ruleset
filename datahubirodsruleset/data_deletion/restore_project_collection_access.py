# /rules/tests/run_test.sh -r restore_project_collection_access -a "/nlmumc/projects/P000000002/C000000001"
import json

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restore_project_collection_access(ctx, user_project_collection):
    user_project = formatters.get_project_path_from_project_collection_path(user_project_collection)

    deletion_state = ""
    for value in row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'deletionState' ".format(user_project),
        AS_LIST,
        ctx.callback,
    ):
        deletion_state = value[0]

    if deletion_state != "":
        ctx.callback.msiExit("-1", "Project deletion state is not valid {}".format(deletion_state))
        return

    for result in row_iterator(
        "COLL_ACCESS_USER_ID",
        "COLL_NAME = '{}'".format(user_project),
        AS_LIST,
        ctx.callback,
    ):
        account_id = result[0]

        for account in row_iterator("USER_NAME", "USER_ID = '{}'".format(account_id), AS_LIST, ctx.callback):
            account_name = account[0]
            ctx.callback.msiSetACL("recursive", "admin:read", account_name, user_project_collection)

    ctx.callback.msiWriteRodsLog("INFO: Users ACL restored  for '{}'".format(user_project_collection), 0)

    project_id = formatters.get_project_id_from_project_collection_path(user_project_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(user_project_collection)

    ctx.callback.msiSetACL("default", "admin:own", "rods", user_project_collection)
    apply_batch_collection_avu_operation(ctx, user_project_collection, "remove")

    ctx.callback.index_update_single_project_collection_metadata(project_id, collection_id, "")
    message = "INFO: Restore to Elasticsearch index the metadata of {}".format(user_project_collection)
    ctx.callback.msiWriteRodsLog(message, 0)

    ctx.callback.msiSetACL("default", "admin:read", "rods", user_project_collection)


def apply_batch_collection_avu_operation(ctx, collection, operation):
    # TODO parameterize operation items. It is hardcoded at the moment
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
                "attribute": "deletionScheduleDate",
                "value": "2023-12-24",
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
