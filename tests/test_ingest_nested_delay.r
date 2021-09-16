# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_ingest_nested_delay.r "*source_collection='/nlmumc/ingest/zones/funny-frog'" "*destination_collection='/nlmumc/projects/P000000010/C000000010'"  | python -m json.tool

def main(rule_args, callback, rei):
    source_collection = global_vars["*source_collection"][1:-1]
    destination_collection = global_vars["*destination_collection"][1:-1]
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.ingest_nested_delay(source_collection, destination_collection, "")

    # Retrieving the rule outcome is done with '["arguments"][1]'
    callback.writeLine("stdout", "Ingest nested delay: done")
    callback.writeLine("stdout", output["arguments"][1])



INPUT *source_collection = '', *destination_collection = ''
OUTPUT ruleExecOut