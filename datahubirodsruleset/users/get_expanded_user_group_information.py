# /rules/tests/run_test.sh -r get_expanded_user_group_information -a "dlinssen;datahub;jmelius" -j
import json

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING

@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_expanded_user_group_information(ctx, participant_names):
    """
    Get the display name and email address of all users (and users in groups) passed to this method
    Also expands groups and get all of the included users' information.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    participant_names: str
        Participan (users or groups) names separated by semicolons

    Returns
    -------
    dict
        A flat dictionary with users and expanded groups
    """

    participant_names = participant_names.split(';')
    users = {}
    rule_result = {}
    for query_result in row_iterator("USER_NAME,USER_TYPE", "", AS_LIST, ctx.callback):
        users[query_result[0]] = query_result[1]
    
    for participant_name in participant_names:
        if users[participant_name] == "rodsuser":
            user_information = json.loads(ctx.callback.get_user_metadata(participant_name, "")["arguments"][1])
            rule_result[participant_name] = {
                "display_name": user_information["displayName"] if user_information["displayName"] else participant_name,
                "email": user_information["email"],
            } 
        elif users[participant_name] == "rodsgroup":
            group_display_name = json.loads(ctx.get_user_attribute_value(participant_name, "displayName", FALSE_AS_STRING, "result")["arguments"][3])
            rule_result[participant_name] = {
                "display_name": group_display_name["value"] if "value" in group_display_name else participant_name
            } 
            for query_result in row_iterator("USER_NAME", "USER_GROUP_NAME = '{}'".format(participant_name), AS_LIST, ctx.callback):
                if query_result[0] not in rule_result:
                    user_information = json.loads(ctx.callback.get_user_metadata(query_result[0], "")["arguments"][1])
                    rule_result[query_result[0]] = {
                        "display_name": user_information["displayName"] if user_information["displayName"] else participant_name,
                        "email": user_information["email"],
                    }
    return rule_result