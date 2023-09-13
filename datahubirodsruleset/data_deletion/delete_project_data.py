# /rules/tests/run_test.sh -r delete_project_data -a "/nlmumc/projects/P000000002,false"

from dhpythonirodsutils.enums import DataDeletionState, DataDeletionAttribute
from dhpythonirodsutils.formatters import format_string_to_boolean
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import IRODS_BACKUP_ACL_BASE_PATH, IRODS_ZONE_BASE_PATH
from datahubirodsruleset.data_deletion.delete_project_collection_data import delete_collection_data
from datahubirodsruleset.data_deletion.restore_project_collection_user_access import (
    check_collection_delete_data_state,
)
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def delete_project_data(ctx, user_project_path, commit):
    """
    Rule to trigger the deletion of all the data files inside the input project.
    All AVUs and metadata files are preserved.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_path : str
        The absolute path of the project
    commit : str
        expected values: "true" or "false". If true, execute the data files deletion.
    """
    commit = format_string_to_boolean(commit)

    ctx.callback.writeLine("stdout", "")
    ctx.callback.writeLine("stdout", "* Running delete_project_data with commit mode as '{}'".format(commit))

    check_collection_delete_data_state(ctx, user_project_path, DataDeletionState.PENDING.value)
    run_delete_project_data(ctx, user_project_path, commit)
    cleanup_delete_project_data(ctx, user_project_path, commit)


def run_delete_project_data(ctx, user_project_path, commit):
    """
    The function to actually trigger the data deletion for all collections inside the project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_path : str
        The absolute path of the project
    commit : bool
        If true, execute the data file deletion.
    """
    ctx.callback.writeLine("stdout", "* Update ACL of rods for {}".format(user_project_path))
    if commit:
        ctx.callback.msiSetACL("recursive", "admin:own", "rods", user_project_path)

    project_collections = []
    for result in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '{}'".format(user_project_path), AS_LIST, ctx.callback):
        project_collections.append(result[0])

    ctx.callback.writeLine("stdout", "* Start deletion for {}".format(user_project_path))
    for collection_path in project_collections:
        ctx.callback.writeLine("stdout", "\t* Loop collection {}".format(collection_path))

        delete_collection_data(ctx, collection_path, commit)


def cleanup_delete_project_data(ctx, user_project_path, commit):
    """
    After deleting the project data, some cleanups actions are required:
        * ACL changes
        * backup collection deletion
        * remove the project DeletionState
        * set the project DeletionState to deleted

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    user_project_path : str
        The absolute path of the project
    commit : bool
        If true, execute the cleanups actions
    """
    if commit:
        backup_project_path = IRODS_BACKUP_ACL_BASE_PATH + user_project_path.replace(IRODS_ZONE_BASE_PATH, "")
        ctx.callback.msiRmColl(backup_project_path, "forceFlag=", 0)
        ctx.callback.msiWriteRodsLog("INFO: Deleted backup project '{}'".format(backup_project_path), 0)
        ctx.callback.remove_collection_attribute_value(user_project_path, DataDeletionAttribute.STATE.value)
        ctx.callback.setCollectionAVU(
            user_project_path, DataDeletionAttribute.STATE.value, DataDeletionState.DELETED.value
        )
        ctx.callback.msiSetACL("default", "admin:read", "rods", user_project_path)
