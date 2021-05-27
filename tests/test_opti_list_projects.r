# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_opti_list_projects.r | python -m json.tool
#
# irule -r irods_rule_engine_plugin-python-instance -F tests/test_list_projects.r | python -m json.tool


from genquery import *

def main(rule_args, callback, rei):
    output = callback.opti("ret")
    callback.writeLine("stdout", output["arguments"][0])


INPUT null
OUTPUT ruleExecOut