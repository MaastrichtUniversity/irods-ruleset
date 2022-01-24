# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_create_ingest_metadata_versions.r "*project_id='P000000014'" "*collection_id='C000000001'"

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    collection_id = global_vars["*collection_id"][1:-1]

    output = callback.create_ingest_metadata_versions(project_id, collection_id)

    callback.writeLine("stdout", "create_ingest_metadata_versions Done")

INPUT *project_id="", *collection_id=""
OUTPUT ruleExecOut
