# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_user_group_memberships.r "*show_special_groups='true'" "*username='jmelius'" | python -m json.tool

def main(rule_args, callback, rei):
    show_special_groups = global_vars["*show_special_groups"][1:-1]
    username = global_vars["*username"][1:-1]

    output = callback.get_user_group_memberships(show_special_groups, username, "result")

    callback.writeLine("stdout", output["arguments"][2])



INPUT *show_special_groups="", *username=""
OUTPUT ruleExecOut