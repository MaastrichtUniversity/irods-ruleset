# /rules/tests/run_test.sh -r get_projects_finance -u opalmen -j
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import avu, metadata_for_paths, query_value
from datahubirodsruleset.projects.get_project_finance import get_projects_finance_details


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_projects_finance(ctx):
    """
    Query the list of projects financial information, if the client user is a PI or data steward

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    dict
        The list of the projects financial information
    """
    username = ctx.callback.get_client_username("")["arguments"][0]

    condition = (
        "COLL_PARENT_NAME = '/nlmumc/projects' AND META_COLL_ATTR_NAME in ("
        f"{query_value(ProjectAVUs.PRINCIPAL_INVESTIGATOR.value)},{query_value(ProjectAVUs.DATA_STEWARD.value)}) "
        f"AND META_COLL_ATTR_VALUE = {query_value(username)}"
    )
    projects = list(dict.fromkeys(row[0] for row in row_iterator("COLL_NAME", condition, AS_LIST, ctx.callback)))
    metadata = metadata_for_paths(ctx, projects, (ProjectAVUs.RESPONSIBLE_COST_CENTER.value, ProjectAVUs.TITLE.value))
    details = {
        path: {
            "project_id": formatters.get_project_id_from_project_path(path),
            "budget_number": avu(ctx, metadata, path, ProjectAVUs.RESPONSIBLE_COST_CENTER.value, fatal=True),
            ProjectAVUs.TITLE.value: avu(ctx, metadata, path, ProjectAVUs.TITLE.value, fatal=True),
        }
        for path in projects
    }

    return [dict(finance, **details[path]) for path, finance in get_projects_finance_details(ctx, projects).items()]
