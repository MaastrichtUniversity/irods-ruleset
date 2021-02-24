# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F test_get_username_attribute_value.r "*username='jmelius'" "*attribute='email'"

def main(rule_args, callback, rei):
    username = global_vars["*username"][1:-1]
    attribute = global_vars["*attribute"][1:-1]

    output = callback.get_username_attribute_value(username, attribute, "result")

    callback.writeLine("stdout", output["arguments"][2])



INPUT *username="", *attribute=""
OUTPUT ruleExecOut