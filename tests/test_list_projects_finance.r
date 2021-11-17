# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_list_projects_finance.r | python -m json.tool

from genquery import *

def main(rule_args, callback, rei):
    output = callback.get_projects_finance("result")
    callback.writeLine("stdout", output["arguments"][0])


INPUT null
OUTPUT ruleExecOut