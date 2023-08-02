# /rules/tests/run_test.sh -r delete_project_collection_data -a "/nlmumc/projects/P000000008/C000000001,false"
import json

from datahubirodsruleset.data_deletion.delete_project_data import delete_collection_data
from datahubirodsruleset.decorator import make, Output


@make(inputs=[0, 1], outputs=[], handler=Output.STORE)
def delete_project_collection_data(ctx, user_project_collection, commit):
    ctx.callback.writeLine("stdout", "")
    ctx.callback.writeLine("stdout", "* Running delete_project_collection_data with commit mode as '{}'".format(commit))

    output = ctx.callback.get_collection_attribute_value(user_project_collection, "deletionState", "result")[
        "arguments"
    ][2]
    deletion_state = json.loads(output)["value"]

    if deletion_state != "pending-for-deletion":
        ctx.callback.msiExit("-1", "Project deletion state is not valid {}".format(deletion_state))
        return

    ctx.callback.writeLine("stdout", "* Update ACL of rods for {}".format(user_project_collection))

    if commit == "true":
        ctx.callback.msiSetACL("recursive", "admin:own", "rods", user_project_collection)

    ctx.callback.writeLine("stdout", "* Start deletion for {}".format(user_project_collection))

    delete_collection_data(ctx, user_project_collection, commit)
