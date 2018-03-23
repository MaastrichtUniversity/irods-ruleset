# This rule will calculate the total number of files in a collection (folder) in iRODS
# Call with
#
# irule -F calcCollectionFiles.r "*collection='/nlmumc/projects/P000000001/'"

irule_dummy() {
    IRULE_calcCollectionFiles(*collection, *result);
    writeLine("stdout", *result);
}

IRULE_calcCollectionFiles(*collection, *result) {
    *count = "0";

    foreach ( *Row in SELECT COUNT(COLL_NAME) WHERE COLL_NAME like "*collection%" AND DATA_REPL_NUM ="0") {
        *count = *Row.COLL_NAME;
    }
    *result = *count;

}

INPUT *collection=""
OUTPUT ruleExecOut