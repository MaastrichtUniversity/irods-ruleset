from dhpythonirodsutils import formatters
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1, 2, 3, 4], outputs=[], handler=Output.STORE)
def set_tape_error_avu(ctx, project_collection_path, username_initiator, attribute, value, message):
    """
    Set the tape error AVU and create a JIRA ticket.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path: str
        The full path of the project collection, e.g. '/nlmumc/projects/P000000017/C000000001'
    username_initiator: str
        The username of the initiator, e.g. dlinssen
    attribute: str
        The A of AVU to set
    value: str
        The V of AVU to be set
    message: str
        The message to be provided in the logs
    """
    ctx.callback.setCollectionAVU(project_collection_path, attribute, value)
    ctx.callback.msiWriteRodsLog(
        "Tape archival/unarchival failed {} with error status '{}'".format(project_collection_path, value), 0
    )

    project_id = formatters.get_project_id_from_project_collection_path(project_collection_path)
    project_collection_id = formatters.get_collection_id_from_project_collection_path(project_collection_path)
    description = ""

    if "value" == "error-archive-failed":
        description = "Archival failed for collection {} in project {}".format(project_collection_id, project_id)
    elif "value" == "error-unarchive-failed":
        description = "Un-archival failed for collection {} in project {}".format(project_collection_id, project_id)

    # if this go wrong always continue
    try:
        ctx.callback.submit_automated_support_request(username_initiator, description, message)
    finally:
        ctx.callback.msiExit("-1", "{} for {}".format(message, project_collection_path))
