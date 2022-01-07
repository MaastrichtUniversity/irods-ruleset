# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_project_resource_availability.r "*project_id='P000000013'" "*ingest='true'" "*destination='false'" "*archive='false'"

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    ingest = global_vars["*ingest"][1:-1]
    destination = global_vars["*destination"][1:-1]
    archive = global_vars["*archive"][1:-1]
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.get_project_resource_availability(project_id, ingest, destination, archive, "")

    # Retrieving the rule outcome is done with '["arguments"][1]'
    callback.writeLine("stdout", output["arguments"][4])


INPUT *project_id="", *ingest="", *destination="", *archive=""
OUTPUT ruleExecOut