# Call with
#
# irule -F createProjectCollection.r "*project='P000000001'" "*title='Testing'"

irule_dummy() {
    IRULE_createProjectCollection(*project, *result, *title);

    writeLine("stdout", *result);
}


# Creates collections in the form C000000001
IRULE_createProjectCollection(*project, *projectCollection, *title) {

    *retry = 0;
    *error = -1;

    # Try to create the dstColl. Exit the loop on success (error = 0) or after too many retries.
    # The while loop adds compatibility for usage in parallellized runs of the delayed rule engine.
    while ( *error < 0 && *retry < 10) {
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

        *retry = *retry + 1;
        *error = errorcode(msiCollCreate(*dstColl, 0, *status));
#        msiWriteRodsLog("DEBUG: Collection '*title' attempt no. *retry : Trying to create *dstColl", 0);
    }

    # Make the rule fail if it doesn't succeed in creating the collection
    if ( *error < 0 && *retry >= 10 ) {
        failmsg(*error, "Collection '*title' attempt no. *retry : Unable to create *dstColl");
    }

    # Add title metadata
    msiAddKeyVal(*titleKV, "title", *title);
    msiSetKeyValuePairsToObj(*titleKV, *dstColl, "-C");
}

INPUT *project=$"P000000001", *title=""
OUTPUT ruleExecOut