# /rules/tests/run_test.sh -r get_project_size -a "/nlmumc/projects/P000000014" -u jmelius -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_size(ctx, project_path):
    """
    Calculate the project size

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_path: str
        Project absolute path

    Returns
    -------
    float
        The project size
    """

    # Calculate size for entire project
    proj_size = float(0)
    for proj_coll in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '" + project_path + "'", AS_LIST, ctx.callback):
        coll_size = float(ctx.callback.get_collection_size(proj_coll[0], "GiB", "none", "")["arguments"][3])
        proj_size = proj_size + coll_size

    return proj_size
