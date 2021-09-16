# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_direct_ingest.r "*username='jmelius'" "*token='funny-frog'"  | python -m json.tool

def main(rule_args, callback, rei):
    username = global_vars["*username"][1:-1]
    token = global_vars["*token"][1:-1]
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.direct_ingest(username, token, "")

    # Retrieving the rule outcome is done with '["arguments"][1]'
    callback.writeLine("stdout", "Direct ingest: done")



INPUT *username = '', *token = ''
OUTPUT ruleExecOut