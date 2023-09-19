# /rules/tests/run_test.sh -r get_project_process_activity -a "P000000002"
from dhpythonirodsutils.enums import DataDeletionAttribute, DataDeletionState
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.collections.get_project_collection_process_activity import check_collection_active_process
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_process_activity(ctx, project_id):
    """
    Query for any process activity linked to the input project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        e.g: P000000001

    Returns
    -------
    dict
        Key: str, describe the activity. Value: bool, True means active.
    """
    has_active_drop_zones = check_active_dropzone_by_project_id(ctx, project_id)
    has_active_processes = check_project_process_activity(ctx, project_id)
    has_pending_deletions = check_pending_deletions_by_project_id(ctx, project_id)

    has_process_activity = False
    if has_active_drop_zones or has_active_processes or has_pending_deletions:
        has_process_activity = True

    project_activity = {
        "has_process_activity": has_process_activity,
        "has_active_collection": check_project_has_active_collection(ctx, project_id),
    }

    return project_activity


def check_project_process_activity(ctx, project_id):
    """
    Query for any project process activity linked to the input project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        e.g: P000000001

    Returns
    -------
    bool
        True, if there is any active process linked to the project.
    """
    query_project_condition = "COLL_PARENT_NAME LIKE '/nlmumc/projects/{}'".format(project_id)

    return check_collection_active_process(ctx, query_project_condition)


def check_active_dropzone_by_project_id(ctx, project_id):
    """
    Query all dropzones and check if any of them is linked to the input project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        e.g: P000000001

    Returns
    -------
    bool
        True, if there is any dropzone linked to the project is active
    """
    parameters = "COLL_NAME, META_COLL_ATTR_VALUE"
    conditions = (
        "COLL_PARENT_NAME in ('/nlmumc/ingest/zones','/nlmumc/ingest/direct') "
        "AND META_COLL_ATTR_NAME = 'project' "
        "AND META_COLL_ATTR_VALUE = '{}'".format(project_id)
    )
    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        token = result[0]
        ctx.callback.msiWriteRodsLog("ERROR: Project '{}' has an active dropzone '{}'".format(project_id, token), 0)

        return True

    return False


def check_pending_deletions_by_project_id(ctx, project_id):
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}' AND COLL_PARENT_NAME LIKE '/nlmumc/projects/{}' ".format(
        DataDeletionAttribute.STATE.value,
        DataDeletionState.PENDING.value,
        project_id,
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        collection_path = result[0]
        attribute = result[1]
        value = result[1]
        ctx.callback.msiWriteRodsLog(
            "ERROR: Project '{}' has '{}' with state: {}:{}".format(project_id, collection_path, attribute, value), 0
        )

        return True

    return False


def check_project_has_active_collection(ctx, project_id):
    """
    Query the collections inside the input project to know if it contains any project collections or all its project
    collections have been deleted.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        e.g: P000000001

    Returns
    -------
    bool
        If false, the project doesn't contain any project collections or all its project collections have been deleted
    """
    number_collections = 0
    number_deleted_collections = 0

    # Query the total number of project collection
    parameters = "count(COLL_NAME)"
    conditions = "COLL_PARENT_NAME LIKE '/nlmumc/projects/{}' ".format(
        project_id,
    )
    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        number_collections = result[0]

    # Query the total number of deleted project collection
    parameters = "count(COLL_NAME)"
    conditions = "META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}' AND COLL_PARENT_NAME LIKE '/nlmumc/projects/{}' ".format(
        DataDeletionAttribute.STATE.value,
        DataDeletionState.DELETED.value,
        project_id,
    )
    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        number_deleted_collections = result[0]

    if number_collections == 0:
        return False
    elif number_deleted_collections == number_collections:
        return False

    return True
