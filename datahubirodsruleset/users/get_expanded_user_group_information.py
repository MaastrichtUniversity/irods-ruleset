# /rules/tests/run_test.sh -r get_expanded_user_group_information -a "dlinssen;datahub;jmelius" -j

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_expanded_user_group_information(ctx, participant_names):
    """
    Get the display name and email address of all users (and users in groups) passed to this method
    Also expands groups and get all the included users' information.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    participant_names: str
        Participant (users or groups) names separated by semicolons

    Returns
    -------
    dict
        A flat dictionary with users and expanded groups
    """
    participant_names = participant_names.split(";")
    participant_names = ", ".join("'{0}'".format(name) for name in participant_names)
    attribute_to_query = "'displayName', 'email'"
    rule_result = {}

    # We can expand a group by passing its name to USER_GROUP_NAME to get its members list with USER_NAME.
    for query_result in row_iterator(
        "USER_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME in ({}) AND META_USER_ATTR_NAME in ({})".format(participant_names, attribute_to_query),
        AS_LIST,
        ctx.callback,
    ):
        user_group = query_result[0]
        attribute = query_result[1]
        value = query_result[2]
        if user_group not in rule_result:
            rule_result[user_group] = {attribute: value}
        else:
            rule_result[user_group][attribute] = value

    return rule_result
