# /rules/tests/run_test.sh -r get_user_internal_affiliation_status -a "jmelius" -j
import json

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_user_internal_affiliation_status(ctx, username):
    """
    Get the user voPersonExternalID and check if the user is part of the UM or MUMC organization.

    Parameters
    ----------
    ctx
    username: str
        The user to check

    Returns
    -------
    bool
        True, if the user is from the UM or MUMC organization. Otherwise, False.
    """
    ret = ctx.get_user_attribute_value(
        username, "voPersonExternalID", FALSE_AS_STRING, "result"
    )["arguments"][3]

    external_id = json.loads(ret).get("value")

    # Early return if empty / None
    if not external_id:
        return False

    # Safely extract affiliation
    parts = external_id.split("@")
    if len(parts) != 2:
        return False

    return parts[1] in {"unimaas.nl", "mumc.nl"}
