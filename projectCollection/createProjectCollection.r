# Call with
#
# irule -F createProjectCollection.r "*project='P000000001'" "*title='Testing'"

irule_dummy() {
    IRULE_createProjectCollection(*project, *result, *title);

    writeLine("stdout", *result);
}


# Creates collections in the form C000000001
IRULE_createProjectCollection(*project, *projectCollection, *title) {

    *max = 0;

    # Find out the current max collection number
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = "/nlmumc/projects/*project" ) {
        uuChopPath(*Row.COLL_NAME, *path, *c);

        *i = int(substr(*c, 1, 10));

        if ( *i > *max ) {
            *max = *i;
        }
    }

    *projectCollection = str(*max + 1);

    # Prepend padding zeros to the name
    while ( strlen(*projectCollection) < 9 ) {
        *projectCollection = "0" ++ *projectCollection;
    }

    *projectCollection = "C" ++ *projectCollection;

    *dstColl = "/nlmumc/projects/*project/*projectCollection";

    msiCollCreate(*dstColl, 0, *status);

    # Add title metadata
    msiAddKeyVal(*titleKV, "title", *title);
    msiSetKeyValuePairsToObj(*titleKV, *dstColl, "-C");
}

INPUT *project=$"P000000001", *title=""
OUTPUT ruleExecOut