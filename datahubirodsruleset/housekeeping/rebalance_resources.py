# Run through the housekeeping controller as rods:
# /rules/tests/run_test.sh -r run_housekeeping -a "rebalance_resources,async" -j
# /rules/tests/run_test.sh -r run_housekeeping -a "rebalance_resources,sync" -j
"""Rebalance each replication resource from a snapshot of the catalog inventory."""

from subprocess import CalledProcessError, PIPE, STDOUT, run  # nosec: argument list, never a shell

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error


def _rebalance_resources(ctx):
    resources = [name for name, in row_iterator(
        "order(RESC_NAME)", "RESC_TYPE_NAME = 'replication'", AS_LIST, ctx.callback
    )]
    results = []
    for resource in resources:
        try:
            completed = run(
                ["iadmin", "modresc", resource, "rebalance"],
                check=True, stdout=PIPE, stderr=STDOUT, text=True, shell=False,
            )
        except CalledProcessError as error:
            results.append({"resource": resource, "execution_status": "failed",
                            "error": str(error), "return_code": error.returncode,
                            "output": (error.stdout or "").strip()})
        except OSError as error:
            results.append({"resource": resource, "execution_status": "failed", "error": str(error)})
        else:
            results.append({"resource": resource, "execution_status": "completed",
                            "output": (completed.stdout or "").strip()})
    failed = sum(result["execution_status"] == "failed" for result in results)
    return {
        "check": "rebalance_resources", "execution_status": "failed" if failed else "completed",
        "summary": {"resources_found": len(resources), "resources_rebalanced": len(resources) - failed,
                    "resources_failed": failed},
        "resources": results,
    }
