# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_collection_size_per_resource.r "*project='P000000015'" | python -m json.tool

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]

    output = callback.get_collection_size_per_resource(project, "")

    callback.writeLine("stdout", output["arguments"][1])

INPUT *project=''
OUTPUT ruleExecOut