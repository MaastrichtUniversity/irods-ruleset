# This rule will calculate the total size in megabytes of a collection (folder) in iRODS
# Call with
#
# irule -F getCollectionSize.r "*collection='/nlmumc/projects/P000000001/'"

irule_dummy() {
    IRULE_getCollectionSize(*collection, *result);
    writeLine("stdout", *result);
}

IRULE_getCollectionSize(*collection, *result) {
    *size = "0";

    foreach ( *Row in SELECT SUM(DATA_SIZE) WHERE COLL_NAME like "*collection%" AND DATA_REPL_NUM ="0") {
        *size = *Row.DATA_SIZE;
        *sizeMB = ceiling(double(*size)/1024/1024);
    }
    *result = *sizeMB;
}

INPUT *collection=""
OUTPUT ruleExecOut