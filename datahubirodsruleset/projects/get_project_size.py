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

    sizes = {}
    for path, value in row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        f"COLL_PARENT_NAME = '{project_path}' AND META_COLL_ATTR_NAME = 'dcat:byteSize'",
        AS_LIST,
        ctx.callback,
    ):
        sizes[path] = value
    return sum((float(value or "0") / 1024 / 1024 / 1024 for value in sizes.values()), 0.0)
