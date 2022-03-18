# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_set_user_attribute_value.r "*username='jmelius'" "*attribute='lastToSAcceptedTimestamp'" "*value='1618476698'"

def main(rule_args, callback, rei):
    username = global_vars["*username"][1:-1]
    attribute = global_vars["*attribute"][1:-1]
    value = global_vars["*value"][1:-1]

    output = callback.set_user_attribute_value(username, attribute, value, "result")

    callback.writeLine("stdout", output["arguments"][2])



INPUT *username="", *attribute="", *value=""
OUTPUT ruleExecOut