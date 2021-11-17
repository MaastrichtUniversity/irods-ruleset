# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_projects_size.r | python -m json.tool

def main(rule_args, callback, rei):
    output = callback.get_projects_size("ret")
    callback.writeLine("stdout", output["arguments"][0])



INPUT *project = ''
OUTPUT ruleExecOut