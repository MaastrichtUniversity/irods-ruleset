# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_set_schema_avu_to_collection.r "*project='P000000001'" "*collection='C000000195'"

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    collection = global_vars["*collection"][1:-1]

    output = callback.set_schema_avu_to_collection(project, collection)


INPUT *project="", *collection=""
OUTPUT ruleExecOut
