# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/test_set_acl_for_metadata_snapshot.r "*project_id='P000000010'" "*collection_id='C000000001'" "*user='jmelius'" "*open_acl='true'" "*close_acl='false'"

def main(rule_args, callback, rei):
    project_id = global_vars["*project_id"][1:-1]
    collection_id = global_vars["*collection_id"][1:-1]
    user = global_vars["*user"][1:-1]
    open_acl = global_vars["*open_acl"][1:-1]
    close_acl = global_vars["*close_acl"][1:-1]

    output = callback.set_acl_for_metadata_snapshot(project_id, collection_id, user, open_acl, close_acl)

    callback.writeLine("stdout", output["arguments"][1])



INPUT *project_id="", *collection_id="", *user="", *open_acl="", *close_acl=""
OUTPUT ruleExecOut