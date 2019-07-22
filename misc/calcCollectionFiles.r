# This rule will calculate the total number of files in a collection (folder) in iRODS
# Call with
#
# irule -F calcCollectionFiles.r "*collection='/nlmumc/projects/P000000001/'"

irule_dummy() {
    IRULE_calcCollectionFiles(*collection, *result);
    writeLine("stdout", *result);
}

IRULE_calcCollectionFiles(*collection, *result) {
    *count = 0;

    # Loop over all distinct files in collection and count the total outside of SQL
    # CAUTION: using count(DATA_ID) inside SQL takes all replicas into consideration, which is not what we want here
    foreach ( *Row in SELECT DATA_ID WHERE COLL_NAME like "*collection%") {
        # not doing anything with the SQL result, just counting the number of iterations in the loop
        *count = *count + 1;
    }
    *result = *count;

}

INPUT *collection=""
OUTPUT ruleExecOut