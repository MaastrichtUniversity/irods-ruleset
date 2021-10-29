# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_user_admin_status.r "*username='dlinssen'"

def main(rule_args, callback, rei):
    username = global_vars["*username"][1:-1]

    output = callback.get_user_admin_status(username, "result")

    callback.writeLine("stdout", output["arguments"][1])



INPUT *username=""
OUTPUT ruleExecOut