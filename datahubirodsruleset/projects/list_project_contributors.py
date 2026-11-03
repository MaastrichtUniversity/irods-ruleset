# /rules/tests/run_test.sh -r list_project_contributors -a "P000000010,false,false" -j -u jmelius
from dhpythonirodsutils import formatters

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import project_acl
from datahubirodsruleset.formatters import format_project_path


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def list_project_contributors(ctx, project_id, inherited, show_service_accounts):
    """
    Get the project's users with 'write' access right

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id : str
        The project's id; e.g: P000000010
    inherited : str
        Role inheritance
        * inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
        * inherited='false' only shows explicit contributors. i.e. A contributor only has 'WRITE' access
    show_service_accounts: str
        'true'/'false' expected; If true, hide the service accounts in the result

    Returns
    -------
    dict
        a json with the lists of groups and users
    """
    return project_acl(
        ctx, format_project_path(ctx, project_id),
        ("own", "modify_object") if formatters.format_string_to_boolean(inherited) else ("modify_object",),
        formatters.format_string_to_boolean(show_service_accounts),
    )
