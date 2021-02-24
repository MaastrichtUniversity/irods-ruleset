# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_project_size.r "*project='/nlmumc/projects/P000000010'" | python -m json.tool

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.get_project_size(project, "")

    # Retrieving the rule outcome is done with '["arguments"][1]'
    callback.writeLine("stdout", output["arguments"][1])



INPUT *project = ''
OUTPUT ruleExecOut