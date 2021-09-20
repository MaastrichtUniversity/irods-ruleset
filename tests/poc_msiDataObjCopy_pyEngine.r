# Call with
#
# irule -r irods_rule_engine_plugin-python-instance -F /rules/tests/poc_msiDataObjCopy_pyEngine.r "*oldPath='/nlmumc/ingest/zones/funny-frog/ncit.owl'" "*newPath='/nlmumc/projects/P000000016/C000000001/ncit.owl'"

def main(rule_args, callback, rei):
    old_path = global_vars["*oldPath"][1:-1]
    new_path = global_vars["*newPath"][1:-1]

    callback.writeLine("stdout", old_path);
    callback.writeLine("stdout", new_path);

    output = callback.msiDataObjCopy(old_path, new_path, "forceFlag=", 0);

    callback.writeLine("stdout", "Copy done");


INPUT *oldPath='', *newPath=''
OUTPUT ruleExecOut
