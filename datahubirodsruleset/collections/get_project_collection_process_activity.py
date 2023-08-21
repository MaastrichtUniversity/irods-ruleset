# /rules/tests/run_test.sh -r get_project_collection_process_activity -a "/nlmumc/projects/P000000001/C000000001"
from dhpythonirodsutils.enums import ProcessAttribute
from genquery import row_iterator, AS_LIST

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_collection_process_activity(ctx, project_collection_path):
    """
    Query for any process activity linked to the input project.

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

    return check_collection_active_process(ctx, query_collection_condition)


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
    conditions = "META_COLL_ATTR_NAME in ('{}', '{}', '{}') AND {} ".format(
        ProcessAttribute.ARCHIVE.value,
        ProcessAttribute.UNARCHIVE.value,
        ProcessAttribute.EXPORTER.value,
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
