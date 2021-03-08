# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_list_project_contributors.r "*project_id='P000000010'" "*inherited='true'" "*show_service_accounts='true'" | python -m json.tool

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    inherited = global_vars["*inherited"][1:-1]
    show_service_accounts = global_vars["*show_service_accounts"][1:-1]

    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.list_project_contributors(project_id, inherited, show_service_accounts, '')

    # Retrieving the rule outcome is done with '["arguments"][0]'
    callback.writeLine("stdout", output["arguments"][3])



INPUT *project_id = "", *inherited="", *show_service_accounts=""
OUTPUT ruleExecOut