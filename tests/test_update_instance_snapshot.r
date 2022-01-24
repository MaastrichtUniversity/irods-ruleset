# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_update_instance_snapshot.r "*project_collection_full_path='/nlmumc/projects/P000000014/C000000001'" "*schema_url='http://mdr.local.dh.unimaas.nl/hdl/P000000014/C000000001/schema.1.json'" "*handle='foobar'"

def main(rule_args, callback, rei):
    project_collection_full_path = global_vars["*project_collection_full_path"][1:-1]
    schema_url = global_vars["*schema_url"][1:-1]
    handle = global_vars["*handle"][1:-1]

    output = callback.update_instance_snapshot(project_collection_full_path, schema_url, handle)

    callback.writeLine("stdout", output["arguments"][1])



INPUT *project_collection_full_path="", *schema_url="", *handle=""
OUTPUT ruleExecOut
