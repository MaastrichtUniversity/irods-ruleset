# /rules/tests/run_test.sh -r get_projects_size -u jmelius -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_projects_size(ctx):
    """
    Query all the (authorized) projects sizes in one query.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    Dict
        Key => project id; Value => Project size
    """

    projects = {}

    for proj_coll in row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME like '/nlmumc/projects/%/%' AND META_COLL_ATTR_NAME = 'dcat:byteSize'",
        AS_LIST,
        ctx.callback,
    ):
        # Split path to id
        project_id = proj_coll[0].split("/")[3]
        # Convert bytes to GiB
        size_gib = float(proj_coll[1]) / 1024 / 1024 / 1024
        if project_id in projects:
            projects[project_id] += size_gib
        else:
            projects[project_id] = size_gib

    return projects
