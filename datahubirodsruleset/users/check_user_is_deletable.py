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
        ctx.callback.msiExit("-1", "Username {} does not exist".format(username))

    # Check if user has the Pending Deletion AVU set (failsafe)
    deletion_avu = json.loads(ctx.get_user_attribute_value(username, "pendingDeletionProcedure", FALSE_AS_STRING, "result")["arguments"][3])["value"]
    ctx.callback.msiWriteRodsLog("deletion_avu = '{}'".format(deletion_avu),0)
    if deletion_avu != TRUE_AS_STRING:
        reasons.append("This user does not have a pending deletion procedure")

    # Check for projects that have this user as DS or PI
    for project in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME like '/nlmumc/projects/%' AND META_COLL_ATTR_NAME IN ('dataSteward','OBI:0000103') AND META_COLL_ATTR_VALUE = '{}'".format(username),
        AS_LIST,
        ctx.callback,
    ):
        reasons.append("{} is the {} for project {}".format(project[2], project[1], project[0]))
    

    # Check for projects with this user as its only manager
    for access_query_results in row_iterator(
        "COLL_ACCESS_USER_ID, COLL_NAME",
        "COLL_ACCESS_NAME = 'own' AND COLL_NAME like '/nlmumc/projects/%' AND COLL_ACCESS_USER_ID = '{}'".format(user_id),
        AS_LIST,
        ctx.callback,
    ):
        project_path = access_query_results[1]
        for num_managers_result in row_iterator(
            "count(COLL_ACCESS_NAME)",
            "COLL_NAME = '{}' AND COLL_ACCESS_NAME ='own'".format(project_path),
            AS_LIST,
            ctx.callback,
        ):
            # 'rods' is always a manager on all projects, so if there's 2 managers and this user is one of them, then there will only be the user 'rods' as a manager afterwards.
            if int(num_managers_result[0]) <= 2:
                reasons.append("{} is the only manager left for project '{}'".format(username, project_path))

    # Check for open dropzones for this user
    for dropzone in row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME like '/nlmumc/ingest/%/%' AND META_COLL_ATTR_NAME = 'creator' AND META_COLL_ATTR_VALUE = '{}'".format(username),
        AS_LIST,
        ctx.callback,
    ):
        reasons.append("{} has an open dropzone {}".format(dropzone[1], dropzone[0]))

    if len(reasons) == 0:
        is_deletable = True

    return {
        "is_deletable": is_deletable,
        "reasons": reasons
    }