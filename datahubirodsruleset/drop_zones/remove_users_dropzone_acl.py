# /rules/tests/run_test.sh -r remove_users_dropzone_acl -a "/nlmumc/ingest/zones/beautiful-hornet"
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.drop_zones.set_project_acl_to_dropzone import get_contributors_for_project_or_dropzone


@make(inputs=[0], outputs=[], handler=Output.STORE)
def remove_users_dropzone_acl(ctx, dropzone_path):
    """
    Revoke all the end user dropzone permissions.
    This is immediate, so the requested dropzone for deletion doesn't appear in any dropzone listing.
    This is an admin rule.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    dropzone_path: str
        The absolute dropzone logical path
    """
    contributors = get_contributors_for_project_or_dropzone(ctx, dropzone_path)

    # Remove permissions of all contributors
    for contributor in contributors:
        ctx.callback.msiSetACL("default", "admin:null", contributor, dropzone_path)
