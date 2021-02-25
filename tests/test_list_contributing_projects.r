# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_list_contributing_projects.r  | python -m json.tool

def main(rule_args, callback, rei):
    output = callback.list_contributing_project("result")

    callback.writeLine("stdout", output["arguments"][0])



INPUT *project_id=""
OUTPUT ruleExecOut