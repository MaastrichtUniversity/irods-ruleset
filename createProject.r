# Call with
#
# irule -F createProject.r

irule_dummy() {
    IRULE_createProject(*result);

    writeLine("stdout", *result);
}


# Creates projects in the form P000000001
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

    # TODO: Determine whether setting defaults here is a good place
    msiAddKeyVal(*metaKV, "title", "no-title");
    msiAddKeyVal(*metaKV, "resource", "replRescUM01");
    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");

    # Set recursive permissions
    msiSetACL("recursive", "inherit", "", *dstColl);
}

INPUT null
OUTPUT ruleExecOut