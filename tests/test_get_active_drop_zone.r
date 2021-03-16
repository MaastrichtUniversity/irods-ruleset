# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_active_drop_zone.r "*token='token'" "*check_ingest_resource_status='false'"

def main(rule_args, callback, rei):
    token = global_vars["*token"][1:-1]
    check_ingest_resource_status = global_vars["*check_ingest_resource_status"][1:-1]

    output = callback.get_active_drop_zone(token, check_ingest_resource_status, "result")

    # Retrieving the rule outcome is done with '["arguments"][3]'
    callback.writeLine("stdout", output["arguments"][2])



INPUT *token="", *check_ingest_resource_status=""
OUTPUT ruleExecOut