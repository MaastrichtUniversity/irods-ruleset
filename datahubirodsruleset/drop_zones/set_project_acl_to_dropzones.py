# /rules/tests/run_test.sh -r set_project_acl_to_dropzones -a "P000000014"
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


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
    query_conditions = "COLL_PARENT_NAME = '/nlmumc/ingest/direct' " \
                       "AND META_COLL_ATTR_NAME = 'project' " \
                       "AND META_COLL_ATTR_VALUE = '{}'".format(project_id)

    for item in row_iterator(query_parameters, query_conditions, AS_LIST, ctx.callback):
        dropzone_path = item[0]
        token = dropzone_path.replace("/nlmumc/ingest/direct/", "")
        ctx.callback.set_project_acl_to_dropzone(project_id, token, "false")
