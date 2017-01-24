# Call with
#
# irule -F listProjectViewers.r "*project='P000000001'"

irule_dummy() {
    IRULE_listProjectViewers(*project, *result);

    writeLine("stdout", *result);
}

IRULE_listProjectViewers(*project,*result) {
    *groups = '[]';
    *groupSize = 0;

    *users = '[]';
    *userSize = 0;

    msiMakeGenQuery("COLL_ACCESS_USER_ID", "COLL_ACCESS_NAME in ('own', 'read object', 'modify object')  and COLL_NAME = '/nlmumc/projects/*project'", *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach ( *Row in *QOut ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';
        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        if ( *objectType == "rodsgroup" ) {
            msi_json_arrayops(*groups, *objectName, "add", *groupSize);
        }

        if ( *objectType == "rodsuser" ) {
            msi_json_arrayops(*users, *objectName, "add", *userSize);
        }

        # objectType rodsadmin are skipped
    }

    *result = '{"users": *users, "groups": *groups }';
}

INPUT *project=$"MUMC-M4I-00001"
OUTPUT ruleExecOut
