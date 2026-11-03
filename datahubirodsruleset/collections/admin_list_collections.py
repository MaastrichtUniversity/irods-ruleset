# /rules/tests/run_test.sh -r admin_list_collections -a "/nlmumc/projects/P000000014" -j
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.collections.list_collections import _list_collections


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def admin_list_collections(ctx, project_path):
    """
    DevOps admin rule:
    Get a listing of all the project's collections that are NOT in the 'deleted' state

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        Project absolute path

    Returns
    -------
    list
        a json list of collections objects that are not 'deleted'
    """
    return _list_collections(ctx, project_path, admin=True)
