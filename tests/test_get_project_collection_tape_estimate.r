# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_project_collection_tape_estimate.r "*project='P000000010'" "*collection='C000000001'" | python -m json.tool

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    collection = global_vars["*collection"][1:-1]

    output = callback.get_project_collection_tape_estimate(project, collection, "result")

    callback.writeLine("stdout", output["arguments"][2])


INPUT *project="", *collection=""
OUTPUT ruleExecOut