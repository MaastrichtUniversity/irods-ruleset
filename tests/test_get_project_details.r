# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_project_details.r "*project='/nlmumc/projects/P000000010'" "*show_service_accounts='true'" | python -m json.tool

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    show_service_accounts = global_vars["*show_service_accounts"][1:-1]
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.get_project_details(project, show_service_accounts, "")

    # Retrieving the rule outcome is done with '["arguments"][1]'
    callback.writeLine("stdout", output["arguments"][2])



INPUT *project = '', *show_service_accounts=""
OUTPUT ruleExecOut