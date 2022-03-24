# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_start_ingest.r "*username='dlinssen'" "*token='crazy-frog'" "*dropzone_type='mounted'"

def main(rule_args, callback, rei):
    username = global_vars["*username"][1:-1]
    token = global_vars["*token"][1:-1]
    dropzone_type = global_vars["*dropzone_type"][1:-1]

    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.start_ingest(username, token, dropzone_type, '')

    callback.writeLine("stdout", output["arguments"][1])

INPUT *username="", *token="", *dropzone_type=""
OUTPUT ruleExecOut