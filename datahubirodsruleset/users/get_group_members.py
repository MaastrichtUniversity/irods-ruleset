# /rules/tests/run_test.sh -r get_group_members -a "datahub" -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_group_members(ctx, group_name):
    """
    Query all members of a group by the input group name.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    group_name : str
        e.g: 'datahub', 'public', 'scannexus'

    Returns
    -------
    dict
        * users: list
        * user_display_names: list
    """
    users = []
    user_display_names = []

    query_parameters = "USER_NAME, META_USER_ATTR_VALUE"
    query_conditions = "USER_GROUP_NAME = '{}' " \
                       "AND USER_TYPE = 'rodsuser' " \
                       "AND META_USER_ATTR_NAME = 'displayName'".format(group_name)

    for result in row_iterator(query_parameters, query_conditions, AS_LIST, ctx.callback):
        if group_name != result[0]:
            users.append(result[0])
            user_display_names.append(result[1])

    output = {
        "users": users,
        "user_display_names": user_display_names,
    }
    return output
