# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_update_instance.r "*project='P000000014'" "*collection='C000000001'" "*handle='21.T12996/P000000014C000000001'" "*version='5'"

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    collection = global_vars["*collection"][1:-1]
    handle = global_vars["*handle"][1:-1]
    version = global_vars["*version"][1:-1]

    output = callback.update_instance(project, collection, handle, version)

    callback.writeLine("stdout", "update_instance Done")



INPUT *project="", *collection="", *handle="" , *version=""
OUTPUT ruleExecOut
