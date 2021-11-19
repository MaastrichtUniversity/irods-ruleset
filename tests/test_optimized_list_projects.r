# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_optimized_list_projects.r | python -m json.tool


from genquery import *

def main(rule_args, callback, rei):
    output = callback.optimized_list_projects("ret")["arguments"][0]
    callback.writeLine("stdout", output)


INPUT null
OUTPUT ruleExecOut