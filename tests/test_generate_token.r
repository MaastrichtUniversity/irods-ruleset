# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_generate_token.r

def main(rule_args, callback, rei):
    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.generate_token("")

    # Retrieving the rule outcome is done with '["arguments"][0]'
    callback.writeLine("stdout", output["arguments"][0])


INPUT *project = ''
OUTPUT ruleExecOut