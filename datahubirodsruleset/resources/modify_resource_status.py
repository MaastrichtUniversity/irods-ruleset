# /rules/tests/run_test.sh -r modify_resource_status -a "replRescUM01,down"
import json

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def modify_resource_status(ctx, resource_name, status):
    """
    Modify the status of a resource (up or down).

    This rule is intended for administrative use via admin-tools.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    resource_name : str
        The name of the resource to modify (e.g., "replRescUM01")
    status : str
        The status to set: "up" or "down"

    Returns
    -------
    str:
        JSON object with result message

    Examples
    --------
    Call from admin-tools:
        irule -F modify_resource_status.r "*resc='replRescUM01'" "*status='down'"

    Or via run_test.sh:
        ./run_test.sh -r modify_resource_status -a "replRescUM01,down" -j
    """
    from subprocess import CalledProcessError, check_call  # nosec

    valid_statuses = ["up", "down"]
    if status not in valid_statuses:
        return json.dumps({
            "success": False,
            "message": f"ERROR: Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
        })

    try:
        check_call(
            ["iadmin", "modresc", resource_name, "status", status],
            shell=False,
        )  # nosec
        return json.dumps({
            "success": True,
            "message": f"Successfully set resource '{resource_name}' status to '{status}'"
        })
    except CalledProcessError as err:
        return json.dumps({
            "success": False,
            "message": f"ERROR: iadmin modresc failed: cmd '{err.cmd}' returncode '{err.returncode}'"
        })