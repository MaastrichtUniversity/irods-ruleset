# /rules/tests/run_test.sh -r set_project_acl_to_dropzones -a "P000000014"
from dhpythonirodsutils import formatters
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.drop_zones.set_project_acl_to_dropzone import (
    get_contributors_for_paths,
    revoke_permissions_dropzone,
    set_own_permissions_dropzone,
)
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.listing_queries import avu, metadata_for_paths
from datahubirodsruleset.utils import FALSE_AS_STRING


@make(inputs=[0], outputs=[], handler=Output.STORE)
def set_project_acl_to_dropzones(ctx, project_id):
    """
    This rule transfers the ACLs that exist on a project level to all of its dropzones
    - Get the 'enableDropzoneSharing' avu on the project
    - Get all drop-zones for the project
    - For each dropzone, depending on the enableDropzoneSharing avu perform the following:
        - Remove all contributors and managers from the drop-zones except for the creator
        - Add all contributors and managers to a dropzone with 'own' rights

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_id: str
        The id of the project to transfer the ACLs from to it's dropzones
    """
    query_parameters = "COLL_NAME"
    query_conditions = (
        f"COLL_PARENT_NAME = '/nlmumc/ingest/direct' AND META_COLL_ATTR_NAME = 'project' AND META_COLL_ATTR_VALUE = '{project_id}'"
    )

    dropzones = [row[0] for row in row_iterator(query_parameters, query_conditions, AS_LIST, ctx.callback)]
    metadata = metadata_for_paths(ctx, dropzones, ("creator", "state"))
    dropzones = [path for path in dropzones if formatters.format_string_to_boolean(
        ctx.callback.is_dropzone_state_ingestable(avu(ctx, metadata, path, "state", FALSE_AS_STRING), "")["arguments"][1]
    )]
    if not dropzones:
        return

    project_path = format_project_path(ctx, project_id)
    sharing_enabled = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.ENABLE_DROPZONE_SHARING.value, "", FALSE_AS_STRING, FALSE_AS_STRING
    )["arguments"][2]
    sharing_enabled = formatters.format_string_to_boolean(sharing_enabled)
    caller = ctx.callback.get_client_username("")["arguments"][0]
    prefix = "admin:" if caller == "rods" else ""

    paths = [project_path] if sharing_enabled else dropzones
    contributors = get_contributors_for_paths(ctx, paths)
    for path in dropzones:
        if sharing_enabled:
            set_own_permissions_dropzone(ctx, path, contributors[project_path], prefix, caller)
        else:
            revoke_permissions_dropzone(ctx, path, contributors[path], prefix, caller, metadata)
