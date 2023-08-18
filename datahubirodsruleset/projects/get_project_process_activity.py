# /rules/tests/run_test.sh -r get_project_process_activity -a "P000000002,false"
from dhpythonirodsutils.enums import ProcessAttribute
from genquery import row_iterator, AS_LIST

from datahubirodsruleset import TRUE_AS_STRING
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_process_activity(ctx, project_id, query_dropzone_activity):
    """
    Query for any process activity linked to the input project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        e.g: P000000001
    query_dropzone_activity: str
        If "true", check if any active dropzone is linked to the input project

    Returns
    -------
    bool
        True, if there is any active process linked to the project.
    """
    project_activity = check_active_processes_by_project_id(ctx, project_id)
    dropzone_activity = False
    if query_dropzone_activity == TRUE_AS_STRING:
        dropzone_activity = check_active_dropzone_by_project_id(ctx, project_id)

    return project_activity or dropzone_activity


def check_active_processes_by_project_id(ctx, project_id):
    """
    Query the input project for any active process (ARCHIVE, UNARCHIVE or EXPORTER). If one is found stop, the rule
    execution.

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
    parameters = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE"
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}', '{}') AND COLL_PARENT_NAME LIKE '/nlmumc/projects/{}' ".format(
        ProcessAttribute.ARCHIVE.value,
        ProcessAttribute.UNARCHIVE.value,
        ProcessAttribute.EXPORTER.value,
        project_id,
    )

    for result in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        process = result[1]
        state = result[2]
        ctx.callback.msiWriteRodsLog(
            "ERROR: Project '{}' has an active process '{}' with the value: '{}'".format(project_id, process, state), 0
        )
        return True

    return False


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
