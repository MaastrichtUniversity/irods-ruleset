# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_pid.r "*project='P000000001'" "*collection='C000000195'"

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    collection = global_vars["*collection"][1:-1]

    output = callback.get_pid(project, collection, "result")

    callback.writeLine("stdout", output["arguments"][2])



INPUT *project="", *collection=""
OUTPUT ruleExecOut