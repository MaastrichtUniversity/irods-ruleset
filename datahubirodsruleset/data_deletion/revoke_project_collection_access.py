# /rules/tests/run_test.sh -r revoke_project_collection_access -a "/nlmumc/projects/P000000002/C000000001"
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import get_elastic_search_connection, COLLECTION_METADATA_INDEX
from datahubirodsruleset.data_deletion.restore_project_collection_access import apply_batch_collection_avu_operation
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def revoke_project_collection_access(ctx, user_project_collection):
    ctx.callback.msiSetACL("default", "admin:own", "rods", user_project_collection)
    # Set 'deletion metadata' AVUs
    apply_batch_collection_avu_operation(ctx, user_project_collection, "add")
    message = "INFO: Set deletion metadata for {}".format(user_project_collection)
    ctx.callback.msiWriteRodsLog(message, 0)
    # ctx.callback.setCollectionAVU(user_project_collection, "deletionReason", "deletionReason")
    # ctx.callback.setCollectionAVU(user_project_collection, "deletionReasonDescription", "deletionReasonDescription")
    # ctx.callback.setCollectionAVU(user_project_collection, "deletionScheduleDate", "2023-12-24")
    # ctx.callback.setCollectionAVU(user_project_collection, "deletionState", "pending-for-deletion")

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

    from elasticsearch import ElasticsearchException

    es = get_elastic_search_connection(ctx)

    project_id = formatters.get_project_id_from_project_collection_path(user_project_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(user_project_collection)

    try:
        es.delete(index=COLLECTION_METADATA_INDEX, id=project_id + "_" + collection_id, ignore=[400, 404])
    except ElasticsearchException:
        ctx.callback.msiWriteRodsLog("ERROR: ElasticsearchException raised during document deletion", 0)
        error_message = "ERROR: Elasticsearch update index failed for {}".format(user_project_collection)
        ctx.callback.msiWriteRodsLog(error_message, 0)

    message = "INFO: Remove from Elasticsearch index the metadata of {}".format(user_project_collection)
    ctx.callback.msiWriteRodsLog(message, 0)
