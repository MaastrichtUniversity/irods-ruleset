# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_validate_metadata.r "*srcColl='/nlmumc/ingest/zones/crazy-frog'"

def main(rule_args, callback, rei):
    source_collection = global_vars["*srcColl"][1:-1]

    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.validate_metadata(source_collection, '')

    # Retrieving the rule outcome is done with '["arguments"][0]'
    callback.writeLine("stdout", output["arguments"][1])

INPUT *srcColl=""
OUTPUT ruleExecOut