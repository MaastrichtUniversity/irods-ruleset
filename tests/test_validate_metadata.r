# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_validate_metadata.r "*token='crazy-frog'"

def main(rule_args, callback, rei):
    token = global_vars["*token"][1:-1]

    # Python-iRODS: When calling a rule without input arguments you need to provide a (empty or nonsense) string, which will contain the output.
    output = callback.validate_metadata(token, '')

    # Retrieving the rule outcome is done with '["arguments"][0]'
    callback.writeLine("stdout", output["arguments"][1])

INPUT *token=""
OUTPUT ruleExecOut