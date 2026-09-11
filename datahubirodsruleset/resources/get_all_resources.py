# /rules/tests/run_test.sh -r get_all_resources
import json
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_resources(ctx):
    """
    Retrieve all resources from the iRODS catalog.

    Intended for admin-tools to list available resources.

    Returns
    -------
    str:
        JSON array of resource names

    Examples
    --------
    Call from admin-tools:
        irule -F get_all_resources.r

    Or via run_test.sh:
        ./run_test.sh -r get_all_resources -j

    Output:
        ["replRescUM01","passRescUM01","ires-hnas-azm",...]
    """
    resources = []
    for result in row_iterator(
        "RESC_NAME",
        "",
        AS_LIST,
        ctx.callback,
    ):
        resources.append(result[0])

    # Return as JSON array for proper parsing
    return json.dumps(resources)