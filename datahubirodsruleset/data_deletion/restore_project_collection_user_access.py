# /rules/tests/run_test.sh -r restore_project_collection_user_access -a "/nlmumc/projects/P000000002/C000000001"
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import DataDeletionAttribute, DataDeletionState
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import FALSE_AS_STRING
from datahubirodsruleset.data_deletion.revoke_project_collection_user_access import apply_collection_deletion_metadata
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[], handler=Output.STORE)
def restore_project_collection_user_access(ctx, user_project_collection):
    """
    Restore the current users access from the parent project ACL to the input project collection ACL
    Additionally:
     * Check if the parent project is still active
     * The project collection metadata need to be also restored in the Elastic search metadata index
     * The 'deletion metadata' need to be removed as AVUs on the project collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_collection : str
        The absolute path of the project collection
    """
    user_project = formatters.get_project_path_from_project_collection_path(user_project_collection)

    check_project_collection_restoration_condition(ctx, user_project, user_project_collection)

    restore_project_collection_user_acl(ctx, user_project, user_project_collection)
    ctx.callback.msiSetACL("default", "admin:own", "rods", user_project_collection)
    remove_collection_deletion_metadata(ctx, user_project_collection)
    restore_project_collection_metadata_from_index(ctx, user_project_collection)
    ctx.callback.msiSetACL("default", "admin:read", "rods", user_project_collection)


def check_project_collection_restoration_condition(ctx, user_project, user_project_collection):
    """
    Check if the project collection has the AVUs states are in the expected states.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project: str
        The absolute path of the project
    user_project_collection : str
        The absolute path of the project collection

    Raises
    -------
    irods.exception.UnknowniRODSError
        Raise an exception if the conditions are not met. (exit status code "-1" == UnknowniRODSError)
    """
    # Check the parent project of the collection is still 'active'
    check_collection_delete_data_state(ctx, user_project, "")

    # Check the project collection has the state (='pending-for-deletion')
    check_collection_delete_data_state(ctx, user_project_collection, DataDeletionState.PENDING.value)


def check_collection_delete_data_state(ctx, collection_path, value_to_check):
    """
    Check if the AVU state conditions are met. Otherwise, stop the rule execution and raise an exception.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    collection_path: str
        The absolute path of the iRODS collection
    value_to_check : str
        The value to compare against the attribute value

    Raises
    -------
    irods.exception.UnknowniRODSError
        Raise an exception if the conditions are not met. (exit status code "-1" == UnknowniRODSError)
    """
    output = ctx.callback.get_collection_attribute_value(collection_path, DataDeletionAttribute.STATE.value, "result")[
        "arguments"
    ][2]
    value = json.loads(output)["value"]

    if value != value_to_check:
        ctx.callback.msiExit(
            "-1",
            "Deletion state is not valid for: {}; Got '{}', but expected '{}'".format(
                collection_path, value, value_to_check
            ),
        )
        return


def restore_project_collection_user_acl(ctx, user_project, user_project_collection):
    """
    Give recursively read access to the project collection for the all current parent project users.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project: str
        The absolute path of the project
    user_project_collection : str
        The absolute path of the project collection
    """
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

    ctx.callback.msiWriteRodsLog("INFO: Users ACL restored for '{}'".format(user_project_collection), 0)


def restore_project_collection_metadata_from_index(ctx, user_project_collection):
    """
    When restoring access to a project collection, the metadata also need to be restored from the Elastic search
    'COLLECTION_METADATA_INDEX'.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_collection : str
        The absolute path of the project collection
    """
    project_id = formatters.get_project_id_from_project_collection_path(user_project_collection)
    collection_id = formatters.get_collection_id_from_project_collection_path(user_project_collection)
    ctx.callback.index_update_single_project_collection_metadata(project_id, collection_id, "")
    message = "INFO: Restore to Elasticsearch index the metadata of {}/{}".format(project_id, collection_id)
    ctx.callback.msiWriteRodsLog(message, 0)


def remove_collection_deletion_metadata(ctx, collection_path):
    """
    Remove all DataDeletionAttributes from the input collection_path.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    collection_path : str
        The absolute path of an iRODS collection (folder).
    """
    reason = ctx.callback.getCollectionAVU(
        collection_path, DataDeletionAttribute.REASON.value, "", "", FALSE_AS_STRING
    )["arguments"][2]
    description = ctx.callback.getCollectionAVU(
        collection_path, DataDeletionAttribute.DESCRIPTION.value, "", "", FALSE_AS_STRING
    )["arguments"][2]
    apply_collection_deletion_metadata(ctx, collection_path, reason, description, "remove")
