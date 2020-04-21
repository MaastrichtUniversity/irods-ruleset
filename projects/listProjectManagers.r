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

    *groupObjects = '[]';
    *groupObjectsSize = 0;

    foreach ( *Row in select COLL_ACCESS_USER_ID where COLL_ACCESS_NAME = 'own' and COLL_NAME = '/nlmumc/projects/*project' ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';

        *objectName = "";
        *objectType = "";

        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        if ( *objectType == "rodsgroup" ) {
            msi_json_arrayops( *groups, *objectName, "add", *groupSize);
            *groupObject = '{ "groupName" : "*objectName", "groupId" : "*objectID" }';
            msi_json_arrayops( *groupObjects, *groupObject, "add", *groupObjectsSize );
        }

        if ( *objectType == "rodsuser" ) {
            msi_json_arrayops(*users, *objectName, "add", *userSize);
        }

        # All other cases of objectType, such as "" or "rodsadmin", are skipped
    }

    *result = '{"users": *users, "groups": *groups, "groupObjects": *groupObjects }';
}

INPUT *project=$"P000000001"
OUTPUT ruleExecOut
