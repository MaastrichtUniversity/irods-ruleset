# /rules/tests/run_test.sh -r get_resource_status -a "passRescUM01"
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_resource_status(ctx, resource_name):
    """
    Queries the resources to get the resource host of the resc that has the directIngestResc AVU

    Returns
    -------
    str:
        The direct ingest resource host
    """
    for result in row_iterator(
        "RESC_STATUS",
        "RESC_NAME = '{}'".format(resource_name),
        AS_LIST,
        ctx.callback,
    ):
        return result[0]