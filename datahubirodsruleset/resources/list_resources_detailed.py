# /rules/tests/run_test.sh -r list_resources_detailed
import json
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_resources_detailed(ctx):
    """
    Retrieve all resources with their status from iRODS.

    Queries RESC_MAIN table for resource details including name, status, and
    context (for S3 resources). Note: Empty status field ("") means the
    resource is "up". Non-empty status indicates "down".

    Intended for admin-tools to list available resources and their current status.

    Returns
    -------
    str:
        JSON array of resource objects with name, status, and context

    Examples
    --------
    Call from admin-tools:
        irule -F list_resources_detailed.r

    Or via run_test.sh:
        ./run_test.sh -r list_resources_detailed -j

    Output:
        [
            {"name":"UM-Ceph-S3-AC","status":"","context":"s3://bucket"},
            {"name":"AZM-storage2","status":"down","context":""},
            ...
        ]

    Note:
    -----
    - Empty status ("") = resource is UP
    - Non-empty status ("down") = resource is DOWN
    - context is only populated for S3 resources
    """
    resources = []
    for result in row_iterator("RESC_NAME, RESC_STATUS, RESC_CONTEXT", "", AS_LIST, ctx.callback):
        resc_name = result[0]
        resc_status = result[1]
        resc_context = result[2]

        # Only include context for S3 resources
        context = resc_context if "S3" in resc_name else ""

        resources.append({
            "name": resc_name,
            "status": resc_status,  # "" = up, "down" = down
            "context": context,
        })

    return json.dumps(resources)