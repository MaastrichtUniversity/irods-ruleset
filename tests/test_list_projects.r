# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_list_projects.r "*show_service_accounts='true'" | python -m json.tool

def main(rule_args, callback, rei):
    show_service_accounts = global_vars["*show_service_accounts"][1:-1]

    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.list_projects(show_service_accounts, '')

    # Retrieving the rule outcome is done with '["arguments"][0]'
    callback.writeLine("stdout", output["arguments"][1])



INPUT *show_service_accounts=""
OUTPUT ruleExecOut