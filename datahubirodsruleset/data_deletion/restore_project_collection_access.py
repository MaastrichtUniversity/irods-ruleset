# /rules/tests/run_test.sh -r restore_project_collection_access -a "/nlmumc/projects/P000000002/C000000001"
from genquery import row_iterator, AS_LIST
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restore_project_collection_access(ctx, user_project_collection):
    user_project = formatters.get_project_path_from_project_collection_path(user_project_collection)

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

    ctx.callback.msiWriteRodsLog("Users ACL restored  for '{}'".format(user_project_collection), 0)
    ctx.callback.msiSetACL("recursive", "admin:read", "rods", user_project_collection)

    project_id = formatters.get_project_id_from_project_collection_path(user_project_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(user_project_collection)

    ctx.callback.index_update_single_project_collection_metadata(project_id, collection_id, "")
    message = "INFO: Restore to Elasticsearch index the metadata of {}".format(user_project_collection)
    ctx.callback.msiWriteRodsLog(message, 0)
