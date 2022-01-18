# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_update_instance_snapshot.r "*instance_location='/nlmumc/projects/P000000014/C000000001/.metadata_versions/instance.1.json'" "*instance_root_location='/nlmumc/projects/P000000014/C000000001/instance.json'" "*schema_url='http://mdr.local.dh.unimaas.nl/hdl/P000000014/C000000001/schema.1.json'" "*handle='foobar'"

def main(rule_args, callback, rei):
    instance_location = global_vars["*instance_location"][1:-1]
    instance_root_location = global_vars["*instance_root_location"][1:-1]
    schema_url = global_vars["*schema_url"][1:-1]
    handle = global_vars["*handle"][1:-1]

    output = callback.update_instance_snapshot(instance_location, schema_url)

    callback.writeLine("stdout", output["arguments"][1])



INPUT *instance_location="", *instance_root_location="", *schema_url="", *handle=""
OUTPUT ruleExecOut