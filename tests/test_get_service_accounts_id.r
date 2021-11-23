# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_service_accounts_id.r | python -m json.tool


from genquery import *

def main(rule_args, callback, rei):
    output = callback.get_service_accounts_id("ret")["arguments"][0]
    callback.writeLine("stdout", output)


INPUT null
OUTPUT ruleExecOut