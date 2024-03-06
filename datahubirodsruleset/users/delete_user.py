# /rules/tests/run_test.sh -r delete_user -a "jmelius" -j

import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def delete_user(ctx, username):
    """
    ! Only callable by RODS !
    Check if the user passed exists, is valid for deletion, and then delete it.
    Errors if the checks do not pass.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username: str
        The username of the user to be deleted
    """
    from subprocess import CalledProcessError, check_call  # nosec

    current_user = ctx.callback.get_client_username("")["arguments"][0]
    # If the user calling this function is someone other than 'rods' (so a project admin)
    # we need to crash, this is an admin only rule
    if current_user != "rods":
        ctx.callback.msiExit("-1", "This rule can only be called by RODS!")

    is_deletable = json.loads(ctx.callback.check_user_is_deletable(username, "result")["arguments"][1])["is_deletable"]
    if not is_deletable:
        ctx.callback.msiExit("-1", "User '{}' is not valid for deletion!".format(username))
    else:
        try:
            check_call(
                [
                    "iadmin",
                    "rmuser",
                    username
                ],
                shell=False,
            )
        except CalledProcessError as err:
            ctx.callback.msiExit("-1", "ERROR: iadmin rmuser: cmd '{}' retcode'{}'".format(err.cmd, err.returncode))

    return json.dumps({"success": True, "deleted_user": username})
