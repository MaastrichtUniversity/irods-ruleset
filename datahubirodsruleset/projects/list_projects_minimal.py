# /rules/tests/run_test.sh -r list_projects_minimal -j
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import avu, collection_metadata


@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_projects_minimal(ctx):
    """
    Get a listing of all (authorized) projects

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    list
        a json list of projects objects
    """

    condition = "COLL_PARENT_NAME = '/nlmumc/projects'"
    paths = [row[0] for row in row_iterator("COLL_NAME", condition, AS_LIST, ctx.callback)]
    metadata = collection_metadata(ctx, condition, (ProjectAVUs.TITLE.value,)) if paths else {}
    return [{
        "id": formatters.get_project_id_from_project_path(path),
        ProjectAVUs.TITLE.value: avu(ctx, metadata, path, ProjectAVUs.TITLE.value, fatal=True),
    } for path in paths]
