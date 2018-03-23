# This rule will calculate the total size of a collection (folder) in iRODS
# Call with
#
# irule -F calcCollectionSize.r "*collection='/nlmumc/projects/P000000001/'" "*unit='GiB'"

irule_dummy() {
    IRULE_calcCollectionSize(*collection, *unit, *result);
    writeLine("stdout", *result);
}

IRULE_calcCollectionSize(*collection, *unit, *result) {
    *sizeBytes = "0";

    foreach ( *Row in SELECT SUM(DATA_SIZE) WHERE COLL_NAME like "*collection%" AND DATA_REPL_NUM ="0") {
        *sizeBytes = *Row.DATA_SIZE;

        if ( *unit == "B" ) {
            *size = ceiling(double(*sizeBytes));
        }
        if ( *unit == "KiB" ) {
            *size = ceiling(double(*sizeBytes)/1024);
        }
        if ( *unit == "MiB" ) {
            *size = ceiling(double(*sizeBytes)/1024/1024);
        }
        if ( *unit == "GiB" ) {
            *size = ceiling(double(*sizeBytes)/1024/1024/1024);
        }
        if ( *unit == "TiB" ) {
            *size = ceiling(double(*sizeBytes)/1024/1024/1024/1024);
        }
    }
    *result = *size;
}

INPUT *collection="",*unit=""
OUTPUT ruleExecOut