# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_update_instance_snapshot.r "*instance_location='/nlmumc/projects/P000000014/C000000001/.metadata_versions/instance_2021-11-29_10-13-03-101799.json'" "*schema_url='http://mdr.local.dh.unimaas.nl/hdl/P000000014/C000000001/schema_2021-11-29_10-49-09-885586'"

def main(rule_args, callback, rei):
    instance_location = global_vars["*instance_location"][1:-1]
    schema_url = global_vars["*schema_url"][1:-1]

    output = callback.update_instance_snapshot(instance_location, schema_url)

    callback.writeLine("stdout", output["arguments"][1])



INPUT *instance_location="", *schema_url=""
OUTPUT ruleExecOut