# /rules/tests/run_test.sh -r list_contributing_projects_by_attribute -a "enableArchive" -j -u jmelius
from dhpythonirodsutils import formatters, validators, exceptions
from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_contributing_projects_by_attribute(ctx, attribute):
    """
    Query the list of projects where the client user is at least a contributor and the action feature is enable for
    the project.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    attribute: str
        The attribute value of a project feature AVU. e.g: 'enableArchive', 'enableUnarchive', 'enableOpenAccessExport',
        'enableContributorEditMetadata'

    Returns
    -------
    dict
        Per project, it returns the project: ID, path, and title
    """
    try:
        validators.validate_project_collections_action_avu(attribute)
    except exceptions.ValidationError:
        ctx.callback.msiExit("-1", "ERROR: ProjectCollectionActions AVU '{}' is not valid".format(attribute))

    projects = []
    access_user_id = ""
    username = ctx.callback.get_client_username("")["arguments"][0]

    for result in row_iterator("USER_GROUP_ID", "USER_NAME = '{}'".format(username), AS_LIST, ctx.callback):
        group_id = "'" + result[0] + "'"
        access_user_id = access_user_id + "," + group_id

    # Remove first comma
    access_user_id = access_user_id[1:]

    parameters = "COLL_NAME"
    conditions = (
        "COLL_ACCESS_NAME in ('own', 'modify object') "
        "and COLL_ACCESS_USER_ID in ({}) "
        "and COLL_PARENT_NAME = '/nlmumc/projects' "
        "and META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = 'true'".format(access_user_id, attribute)
    )

    for project_path in row_iterator(parameters, conditions, AS_LIST, ctx.callback):
        project = {
            "id": formatters.get_project_id_from_project_path(project_path[0]),
            "path": project_path[0],
            ProjectAVUs.TITLE.value: ctx.callback.getCollectionAVU(
                project_path[0], ProjectAVUs.TITLE.value, "", "", TRUE_AS_STRING
            )["arguments"][2]
        }
        projects.append(project)

    return projects
