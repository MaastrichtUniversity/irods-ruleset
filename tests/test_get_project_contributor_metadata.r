# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_get_project_contributor_metadata.r "*project_id='P000000010'" | python -m json.tool

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]

    output = callback.get_project_contributors_metadata(project_id, "result")

    callback.writeLine("stdout", output["arguments"][1])



INPUT *project_id=""
OUTPUT ruleExecOut