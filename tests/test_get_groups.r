# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_groups.r "*show_special_groups='false'"  | python -m json.tool

def main(rule_args, callback, rei):
    show_special_groups = global_vars["*show_special_groups"][1:-1]

    output = callback.get_groups(show_special_groups, "result")

    callback.writeLine("stdout", output["arguments"][1])



INPUT *show_special_groups=""
OUTPUT ruleExecOut