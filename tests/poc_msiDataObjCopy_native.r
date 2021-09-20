# Call with
#
# irule -F /rules/tests/poc_msiDataObjCopy_native.r "*oldPath='/nlmumc/ingest/zones/funny-frog/ncit.owl'" "*newPath='/nlmumc/projects/P000000016/C000000001/ncit.owl'"

irule_dummy() {
    IRULE_POC_DataObjCopy(*oldPath, *newPath);
}

IRULE_POC_DataObjCopy(*oldPath, *newPath) {
    writeLine("stdout", *oldPath);
    writeLine("stdout", *newPath);
    msiDataObjCopy(*oldPath, *newPath, "forceFlag=", 0);
    writeLine("stdout", "Copy done");
}

INPUT *oldPath='', *newPath=''
OUTPUT ruleExecOut
