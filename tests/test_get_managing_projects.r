# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_managing_projects.r "*project_id='P000000010'" "*show_service_accounts='true'" | python -m json.tool

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    show_service_accounts = global_vars["*show_service_accounts"][1:-1]

    output = callback.get_managing_projects(project_id, show_service_accounts, "result")

    callback.writeLine("stdout", output["arguments"][2])



INPUT *project_id="", *show_service_accounts=""
OUTPUT ruleExecOut