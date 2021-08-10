# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_set_dropzone_total_files_avu.r "*token='vast-chinchilla'"

def main(rule_args, callback, rei):
    token = global_vars["*token"][1:-1]

    output = callback.set_dropzone_total_files_avu(token, "result")

    callback.writeLine("stdout", output["arguments"][0])



INPUT *token=""
OUTPUT ruleExecOut