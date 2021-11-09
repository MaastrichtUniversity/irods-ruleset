# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_fill_instance.r "*project='P000000001'" "*collection='C000000195'" "*handle='21.T12996/P000000001C000000195'"

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    collection = global_vars["*collection"][1:-1]
    handle = global_vars["*handle"][1:-1]

    output = callback.fill_instance(project, collection, handle)

    callback.writeLine("stdout", output["arguments"][2])



INPUT *project="", *collection="", *handle=""
OUTPUT ruleExecOut