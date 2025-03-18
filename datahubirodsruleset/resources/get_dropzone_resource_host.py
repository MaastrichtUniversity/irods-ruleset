# /rules/tests/run_test.sh -r get_dropzone_resource_host -a "mounted,P000000002"
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from dhpythonirodsutils.enums import ProjectAVUs
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_dropzone_resource_host(ctx, dropzone_type, project_id):
    """
    If the dropzone is direct, returns the Direct ingest resource host, if not, returns
    resource host for the resource listed on the project

    Returns
    -------
    str:
        The ingest resource host, ie 'fhml-srv079.unimaas.nl'
    """
    if dropzone_type == "direct":
        ingest_resource_host = ctx.callback.get_direct_ingest_resource_host("")["arguments"][0]
    else:
        ingest_resource = ctx.callback.getCollectionAVU(
            format_project_path(ctx, project_id), ProjectAVUs.INGEST_RESOURCE.value, "", "", TRUE_AS_STRING
        )["arguments"][2]
        # Obtain the resource host from the specified ingest resource
        for row in row_iterator("RESC_LOC", "RESC_NAME = '{}'".format(ingest_resource), AS_LIST, ctx.callback):
            ingest_resource_host = row[0]
    return ingest_resource_host