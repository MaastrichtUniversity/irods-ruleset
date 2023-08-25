# /rules/tests/run_test.sh -r revoke_project_collection_user_access -a "/nlmumc/projects/P000000002/C000000001,reason42,description24"
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionAttribute, DataDeletionState
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import (
    get_elastic_search_connection,
    COLLECTION_METADATA_INDEX,
    apply_batch_collection_avu_operation,
    apply_batch_acl_operation,
)
from datahubirodsruleset.collections.get_project_collection_process_activity import (
    check_project_collection_process_activity,
)
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2], outputs=[], handler=Output.STORE)
def revoke_project_collection_user_access(ctx, user_project_collection, reason, description):
    """
    After a user request a project collection deletion, all users accesses need to be revoked immediately.
    Additionally:
     * Check if there are any ongoing process linked to the project. If true, stop the rule execution
     * The project collection metadata need to be also deleted in the Elastic search metadata index
     * The 'deletion metadata' need to be set as AVUs on the project collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_collection : str
        The absolute path of the project collection
    reason : str
        The reason of the deletion
    description : str
        An optional description providing additional details, empty string if not provided by the form/user
    """
    project_id = formatters.get_project_id_from_project_collection_path(user_project_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(user_project_collection)

    if check_project_collection_process_activity(ctx, user_project_collection):
        ctx.callback.msiExit("-1", "Stop execution, active proces(ses) found for {}".format(user_project_collection))
        return

    ctx.callback.msiSetACL("default", "admin:own", "rods", user_project_collection)
    apply_collection_deletion_metadata(ctx, user_project_collection, reason, description, "add")
    revoke_project_collection_user_acl(ctx, user_project_collection)
    delete_project_collection_metadata_from_index(ctx, project_id, collection_id)
    ctx.callback.msiSetACL("default", "admin:read", "rods", user_project_collection)


def delete_project_collection_metadata_from_index(ctx, project_id, collection_id):
    """
    When revoking access to a project collection, the metadata also need to be deleted from the Elastic search
    'COLLECTION_METADATA_INDEX'.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        e.g: P000000001
    collection_id: str
        e.g: C000000001
    """
    from elasticsearch import ElasticsearchException

    es = get_elastic_search_connection(ctx)

    try:
        es.delete(index=COLLECTION_METADATA_INDEX, id=project_id + "_" + collection_id, ignore=[400, 404])
    except ElasticsearchException:
        ctx.callback.msiWriteRodsLog("ERROR: ElasticsearchException raised during document deletion", 0)
        error_message = "ERROR: Elasticsearch update index failed for {}/{}".format(project_id, collection_id)
        ctx.callback.msiWriteRodsLog(error_message, 0)

    message = "INFO: Remove from Elasticsearch index the metadata of {}/{}".format(project_id, collection_id)
    ctx.callback.msiWriteRodsLog(message, 0)


def revoke_project_collection_user_acl(ctx, user_project_collection):
    """
    Loop over the ACL of the project collection and remove all end-users access (not admins or service-accounts)

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_collection: str
        Absolute iRODS collection path. e.g: /nlmumc/projects/P000000011/C000000001
    """
    # The ACL changes on the project collection root are executed immediately
    acl_operations = []
    # But the recursive ACL changes are executed in the delay queue
    delay_set_acl_rule_body = ""
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
                acl_operation = {
                    "entity_name": account_name,
                    "acl": "null",
                }
                acl_operations.append(acl_operation)

                rule_body = "msiSetACL('recursive', 'admin:null', '{}', '{}');".format(
                    account_name, user_project_collection
                )
                delay_set_acl_rule_body += rule_body

    apply_batch_acl_operation(ctx, user_project_collection, acl_operations)
    ctx.delayExec(
        "<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>",
        delay_set_acl_rule_body,
        "",
    )
    ctx.callback.msiWriteRodsLog(
        "INFO: Users ACL revoked for project collection '{}'".format(user_project_collection), 0
    )


def apply_collection_deletion_metadata(ctx, collection_path, reason, description, operation_type):
    """
    Set all DataDeletionAttributes with the user input values.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    collection_path : str
        The absolute path of iRODS collection
    reason : str
        The reason of the deletion
    description : str
        Optional, the description text for the deletion
    operation_type: str
        expected values: "add" or "remove"
    """
    deletion_metadata = {
        DataDeletionAttribute.REASON.value: reason,
        DataDeletionAttribute.STATE.value: DataDeletionState.PENDING.value,
    }
    if description:
        deletion_metadata[DataDeletionAttribute.DESCRIPTION.value] = description

    apply_batch_collection_avu_operation(ctx, collection_path, operation_type, deletion_metadata)
