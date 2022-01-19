# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_versioned_pids.r "*project='P000000014'" "*collection='C000000001'" "*version='2'"

def main(rule_args, callback, rei):
    project = global_vars["*project"][1:-1]
    collection = global_vars["*collection"][1:-1]
    version = global_vars["*version"][1:-1]

    output = callback.get_versioned_pids(project, collection, version, "")

    callback.writeLine("stdout", output["arguments"][3])



INPUT *project="", *collection="", *version=""
OUTPUT ruleExecOut
