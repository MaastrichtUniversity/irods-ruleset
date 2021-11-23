# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_list_contributing_projects.r "*show_service_accounts='true'" | python -m json.tool

def main(rule_args, callback, rei):
    show_service_accounts = global_vars["*show_service_accounts"][1:-1]
    output = callback.list_contributing_projects(show_service_accounts, "result")

    callback.writeLine("stdout", output["arguments"][1])



INPUT *show_service_accounts=""
OUTPUT ruleExecOut