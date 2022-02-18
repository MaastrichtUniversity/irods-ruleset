# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_update_metadata_during_edit_collection.r "*project_id='P000000014'" "*collection_id='C000000001'" "*version='7'"

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    collection_id = global_vars["*collection_id"][1:-1]
    version = global_vars["*version"][1:-1]

    output = callback.update_metadata_during_edit_collection(project_id, collection_id, version)

    callback.writeLine("stdout", output["arguments"][1])



INPUT *project_id="", *collection_id="", *version=""
OUTPUT ruleExecOut
