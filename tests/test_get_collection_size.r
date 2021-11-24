# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_collection_size.r "*collection='/nlmumc/projects/P000000013/C000000001'" "*unit='MiB'" "*round='ceiling'"

def main(rule_args, callback, rei):
    collection = global_vars["*collection"][1:-1]
    unit = global_vars["*unit"][1:-1]
    round = global_vars["*round"][1:-1]

    output = callback.get_collection_size(collection, unit, round, "result")

    # Retrieving the rule outcome is done with '["arguments"][3]'
    callback.writeLine("stdout", output["arguments"][3])



INPUT *collection="", *unit="", *round=""
OUTPUT ruleExecOut