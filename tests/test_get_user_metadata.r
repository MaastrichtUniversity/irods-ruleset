# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_user_metadata.r "*username='jmelius'" | python -m json.tool

def main(rule_args, callback, rei):
    username = global_vars["*username"][1:-1]

    output = callback.get_user_metadata(username, "result")

    callback.writeLine("stdout", output["arguments"][1])



INPUT *username=""
OUTPUT ruleExecOut