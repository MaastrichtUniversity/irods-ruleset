# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_project_ingest_availability.r "*project_id='P000000013'" "*check_destination_resource='true'" | python -m json.tool

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    check_destination_resource = global_vars["*check_destination_resource"][1:-1]
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.get_project_ingest_availability(project_id, check_destination_resource, "")

    # Retrieving the rule outcome is done with '["arguments"][1]'
    callback.writeLine("stdout", output["arguments"][2])



INPUT *project_id = '', *check_destination_resource=""
OUTPUT ruleExecOut