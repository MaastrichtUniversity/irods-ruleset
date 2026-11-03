# /rules/tests/run_test.sh -r list_project_managers -a "P000000010,false" -j -u jmelius
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import project_acl
from datahubirodsruleset.formatters import format_project_path


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def list_project_managers(ctx, project_id, show_service_accounts):
    """
    Get the project's users with 'own' access right

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        a json with the lists of groups and users
    """
    return project_acl(
        ctx, format_project_path(ctx, project_id),
        ("own",),
        formatters.format_string_to_boolean(show_service_accounts),
    )
