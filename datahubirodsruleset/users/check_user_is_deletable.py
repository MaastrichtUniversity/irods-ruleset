# /rules/tests/run_test.sh -r check_user_is_deletable -a "dlinssen" -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

import json
from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, TRUE_AS_STRING


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def check_user_is_deletable(ctx, username):
    """
    Check if a user passed in iRODS is a
      PI 
      Data Steward
      the last manager for a specific project
      has open dropzones

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    username:
        The username of the user to check

    Returns
    -------
    Dict
        Key => project id; Value => Project size
    """

    is_deletable = False
    reasons = []

    # Check if the user exists
    user_id = ctx.callback.get_user_id(username, "")["arguments"][1]
    if not user_id:
        ctx.callback.msiExit("-1", f"Username {username} does not exist")

    # Check if user has the Pending Deletion AVU set (failsafe)
    deletion_avu = json.loads(ctx.get_user_attribute_value(username, "pendingDeletionProcedure", FALSE_AS_STRING, "result")["arguments"][3])["value"]
    if deletion_avu != TRUE_AS_STRING:
        reasons.append("This user does not have a pending deletion procedure")

    # Check for projects that have this user as DS or PI
    for project in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        f"COLL_PARENT_NAME = '/nlmumc/projects' AND META_COLL_ATTR_NAME IN ('dataSteward','OBI:0000103') AND META_COLL_ATTR_VALUE = '{username}'",
        AS_LIST,
        ctx.callback,
    ):
        reasons.append(f"{project[2]} is the {project[1]} for project {project[0]}")
    

    # Fetch project owners once; descendant collections do not define project managers.
    project_managers = {}
    for project_path, manager_id in row_iterator(
        "COLL_NAME, COLL_ACCESS_USER_ID",
        "COLL_ACCESS_NAME = 'own' AND COLL_PARENT_NAME = '/nlmumc/projects'",
        AS_LIST,
        ctx.callback,
    ):
        project_managers.setdefault(project_path, set()).add(manager_id)

    for project_path, managers in project_managers.items():
        # 'rods' is always a manager, so two owners means only 'rods' would remain.
        if user_id in managers and len(managers) <= 2:
            reasons.append(f"{username} is the only manager left for project '{project_path}'")

    # Check for open dropzones for this user
    for dropzone in row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        f"COLL_NAME like '/nlmumc/ingest/%/%' AND META_COLL_ATTR_NAME = 'creator' AND META_COLL_ATTR_VALUE = '{username}'",
        AS_LIST,
        ctx.callback,
    ):
        reasons.append(f"{dropzone[1]} has an open dropzone {dropzone[0]}")

    if len(reasons) == 0:
        is_deletable = True

    return {
        "is_deletable": is_deletable,
        "reasons": reasons
    }
