# /rules/tests/run_test.sh -r get_direct_ingest_resource_host
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_direct_ingest_resource_host(ctx):
    """
    Queries the resources to get the resource host of the resc that has the directIngestResc AVU

    Returns
    -------
    str:
        The direct ingest resource host
    """
    # Obtain the resource host from the specified ingest resource
    for row in row_iterator(
        "RESC_LOC, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE",
        "META_RESC_ATTR_NAME = 'directIngestResc' AND META_RESC_ATTR_VALUE = 'true'",
        AS_LIST,
        ctx.callback,
    ):
        direct_ingest_resource_host = row[0]

    return direct_ingest_resource_host
