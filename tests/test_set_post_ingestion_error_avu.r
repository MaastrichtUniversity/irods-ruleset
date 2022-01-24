# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_set_post_ingestion_error_avu.r "*project_id='P000000014'" "*collection_id='C000000001'" "*dropzone='/nlmumc/ingest/zones/vast-chinchilla'" "*message='CRASH'"

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    collection_id = global_vars["*collection_id"][1:-1]
    dropzone = global_vars["*dropzone"][1:-1]
    message = global_vars["*message"][1:-1]

    callback.set_post_ingestion_error_avu(project_id, collection_id, dropzone, message)

    callback.writeLine("stdout", "Should never happen")

INPUT *project_id="", *collection_id="", *dropzone="",  *message=""
OUTPUT ruleExecOut

