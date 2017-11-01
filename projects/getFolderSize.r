# This rule will calculate the total size in megabytes of a collection (folder) in iRODS
# Call with
#
# irule -F getFolderSize.r "*folder='/nlmumc/projects/P000000001/'"

irule_dummy() {
    IRULE_getFolderSize(*folder, *result);
    writeLine("stdout", *result);
}

IRULE_getFolderSize(*folder, *result) {
    *size = "0";

    foreach ( *Row in SELECT SUM(DATA_SIZE) WHERE COLL_NAME like "*folder%" AND DATA_REPL_NUM ="0") {
        *size = *Row.DATA_SIZE;
        *sizeMB = ceiling(double(*size)/1024/1024);
    }
    *result = *sizeMB;
}

INPUT *folder=""
OUTPUT ruleExecOut