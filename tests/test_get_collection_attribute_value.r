# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_collection_attribute_value.r "*path='/nlmumc/projects/P000000010/C000000001'" "*attribute='archiveState'"

def main(rule_args, callback, rei):
    path = global_vars["*path"][1:-1]
    attribute = global_vars["*attribute"][1:-1]

    output = callback.get_collection_attribute_value(path, attribute, "result")

    callback.writeLine("stdout", output["arguments"][2])



INPUT *path="", *attribute=""
OUTPUT ruleExecOut