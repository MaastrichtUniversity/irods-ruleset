# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_remove_size_ingested_avu.r "*path='/nlmumc/projects/P000000010/C000000001'"

def main(rule_args, callback, rei):
    path = global_vars["*path"][1:-1]

    output = callback.remove_size_ingested_avu(path, "")

    callback.writeLine("stdout", output["arguments"][0])



INPUT *path=""
OUTPUT ruleExecOut