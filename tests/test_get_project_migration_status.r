# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_project_migration_status.r "*project_path='/nlmumc/projects/P000000010'" | python -m json.tool

def main(rule_args, callback, rei):
    project_path = global_vars["*project_path"][1:-1]

    output = callback.get_project_migration_status(project_path, "")

    callback.writeLine("stdout", output["arguments"][1])



INPUT *project_path = ''
OUTPUT ruleExecOut