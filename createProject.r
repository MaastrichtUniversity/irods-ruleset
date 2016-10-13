# Call with
#
# irule -F createProject.r

irule_dummy() {
    IRULE_createProject(*result);

    writeLine("stdout", *result);
}


# Creates collections in the form C000000001
IRULE_createProject(*project) {

    *max = 0;

    # Find out the current max project number
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects' ) {
        uuChopPath(*Row.COLL_NAME, *path, *c);

        *i = int(substr(*c, 1, 10));

        if ( *i > *max ) {
            *max = *i;
        }
    }

    *project = str(*max + 1);

    # Prepend padding zeros to the name
    while ( strlen(*project) < 9 ) {
        *project = "0" ++ *project;
    }

    *project = "P" ++ *project;

    *dstColl = /nlmumc/projects/*project;

    msiCollCreate(*dstColl, 0, *status);
}

INPUT null
OUTPUT ruleExecOut