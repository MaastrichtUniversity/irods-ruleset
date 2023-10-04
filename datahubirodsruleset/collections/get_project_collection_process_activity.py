# /rules/tests/run_test.sh -r get_project_collection_process_activity -a "/nlmumc/projects/P000000001/C000000001"
import json

from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProcessAttribute
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_collection_process_activity(ctx, project_collection_path):
    """
    Query for any process activity linked to the input project collection.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path: str
        Project collection absolute path

    Returns
    -------
    bool
        True, if there is any active process linked to the project.
    """

    return check_project_collection_process_activity(ctx, project_collection_path)


def check_project_collection_process_activity(ctx, project_collection_path):
    """
    Private function of 'get_project_collection_process_activity'.
    Meant to be call as a python function and not as a rule with @make
    """
    query_collection_condition = "COLL_NAME = '{}'".format(project_collection_path)

    active_process = check_collection_active_process(ctx, query_collection_condition)
    active_dropzone = check_active_dropzone_by_project_collection_path(ctx, project_collection_path)

    return active_process or active_dropzone


def check_collection_active_process(ctx, query_collection_condition):
    """
    Query the input project for any active process (ARCHIVE, UNARCHIVE or EXPORTER). If one is found stop, the rule
    execution.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    query_collection_condition: str
        query condition string to know whether the query is executed on one project collection or all collection in
        the project

    Returns
    -------
    bool
        True, if there is any active process linked to the project.
    """
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}') AND {} ".format(
        ProcessAttribute.ARCHIVE.value,
        ProcessAttribute.UNARCHIVE.value,
        query_collection_condition,
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        process = result[1]
        state = result[2]
        message = "ERROR: '{}' has an active process '{}' with state: '{}'".format(
            query_collection_condition, process, state
        )
        ctx.callback.msiWriteRodsLog(message, 0)

        return True

    return False


def check_active_dropzone_by_project_collection_path(ctx, project_collection_path):
    """
    Query all dropzones and check if any of them is linked to the input project collection.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path: str
        Project collection absolute path. /nlmumc/projects/P000000008/C000000003

    Returns
    -------
    bool
        True, if there is any dropzone linked to the project is active
    """
    project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
    collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)

    ret = ctx.callback.listActiveDropZones("false", "")["arguments"][1]
    drop_zones = json.loads(ret)

    for drop_zone in drop_zones:
        if drop_zone["project"] == project_id and drop_zone["destination"] == collection_id:
            message = "ERROR: '{}' has an active dropzone '{}' with state: '{}'".format(
                project_collection_path, drop_zone["token"], drop_zone["state"]
            )
            ctx.callback.msiWriteRodsLog(message, 0)

            return True

    return False
