# Call with
#
# irule -F listProjectManagers.r "*project='P000000001'"

irule_dummy() {
    IRULE_listProjectManagers(*project, *result);

    writeLine("stdout", *result);
}

IRULE_listProjectManagers(*project, *result) {
    *groups = '[]';
    *groupSize = 0;

    *users = '[]';
    *userSize = 0;

    foreach ( *Row in select COLL_ACCESS_USER_ID where COLL_ACCESS_NAME = 'own' and COLL_NAME = '/nlmumc/projects/*project' ) {
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
