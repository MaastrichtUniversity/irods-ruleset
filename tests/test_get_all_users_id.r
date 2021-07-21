# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_all_users_id.r | python -m json.tool

def main(rule_args, callback, rei):
    output = callback.get_all_users_id("ret")
    callback.writeLine("stdout", output["arguments"][0])



INPUT *project = ''
OUTPUT ruleExecOut