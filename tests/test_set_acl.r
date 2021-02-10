# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F set_acl.r "*mode='default'" "*access_level='own'" "*user='jmelius'" "*path='/nlmumc/projects/P000000010'"

def main(rule_args, callback, rei):
    mode = global_vars["*mode"][1:-1]
    access_level = global_vars["*access_level"][1:-1]
    user = global_vars["*user"][1:-1]
    path = global_vars["*path"][1:-1]

    output = callback.set_acl(mode, access_level, user, path)

    callback.writeLine("stdout", "Done")



INPUT *mode="", *access_level="", *user="", *path=""
OUTPUT ruleExecOut