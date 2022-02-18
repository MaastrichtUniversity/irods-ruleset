# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/create_ingest_metadata_snapshot.r "*project_id='P000000014'" "*collection_id='C000000001'" "*source_collection='/nlmumc/ingest/zones/crazy-frog'" "*overwrite_flag='false'"

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    collection_id = global_vars["*collection_id"][1:-1]
    source_collection = global_vars["*source_collection"][1:-1]
    overwrite_flag = global_vars["*overwrite_flag"][1:-1]

    output = callback.create_ingest_metadata_snapshot(project_id, collection_id, source_collection, overwrite_flag)

    callback.writeLine("stdout", "create_ingest_metadata_versions Done")

INPUT *project_id="", *collection_id="", *source_collection="", *overwrite_flag=""
OUTPUT ruleExecOut
