# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_user_or_group_by_id.r "*id='10043'" | python -m json.tool


from genquery import *

def main(rule_args, callback, rei):
    id = global_vars["*id"][1:-1]
    output = callback.get_user_or_group_by_id(id, "ret")
    callback.writeLine("stdout", output["arguments"][1])


INPUT *id=""
OUTPUT ruleExecOut