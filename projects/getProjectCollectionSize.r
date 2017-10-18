# Call with
#
# irule -F getProjectCollectionSize.r "*project='P000000001'" "*projectCollection='C000000001'"

irule_dummy() {
    IRULE_getProjectCollectionSize(*project, *projectCollection,*result);
    writeLine("stdout", *result);
}

IRULE_getProjectCollectionSize(*project, *projectCollection,*result) {
    *size = "0";

    foreach ( *Row in select sum(DATA_SIZE) where COLL_NAME like "/nlmumc/projects/*project/*projectCollection%" AND DATA_REPL_NUM ="0") {
        *size = *Row.DATA_SIZE;
    }
    *result = *size;
}

INPUT *project="P000000001", *projectCollection='C000000001'
OUTPUT ruleExecOut