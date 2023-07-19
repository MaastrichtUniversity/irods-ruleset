# /rules/tests/run_test.sh -r create_project_collection -a "P000000002,CollectionTitle"
from dhpythonirodsutils.enums import ProjectAVUs

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path, format_project_collection_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def create_project_collection(ctx, project_id, title):
    """

    Parameters
    ----------
    ctx
    project_id
    title

    Returns
    -------

    """
    retry = 0
    error = -1
    new_project_collection_path = ""
    project_collection_id = ""
    project_path = format_project_path(ctx, project_id)

    # Try to create the new_project_path. Exit the loop on success (error = 0) or after too many retries.
    # The while loop adds compatibility for usage in parallelized runs of the delayed rule engine.
    while error < 0 and retry < 10:
        latest_project_collection_number = ctx.callback.getCollectionAVU(
            project_path, "latest_project_collection_number", "*latest_project_collection_number", "", TRUE_AS_STRING
        )["arguments"][2]
        new_latest = int(latest_project_collection_number) + 1
        project_collection_id = str(new_latest)
        while len(project_collection_id) < 9:
            project_collection_id = "0" + str(project_collection_id)
        project_collection_id = "C" + project_collection_id

        new_project_collection_path = format_project_collection_path(ctx, project_id, project_collection_id)

        retry = retry + 1
        try:
            ctx.callback.msiCollCreate(new_project_collection_path, 0, 0)
        except RuntimeError:
            error = -1
        else:
            error = 0

    # Make the rule fail if it doesn't succeed in creating the project
    if error < 0 and retry >= 10:
        msg = "ERROR: Collection '{}' attempt no. {} : Unable to create {}".format(
            title, retry, new_project_collection_path
        )
        ctx.callback.msiExit(str(error), msg)

    ctx.callback.setCollectionAVU(new_project_collection_path, ProjectAVUs.TITLE.value, title)

    return project_collection_id
