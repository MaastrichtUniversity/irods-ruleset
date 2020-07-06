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

    *userObjects = '[]';
    *userObjectsSize = 0;

    foreach ( *Row in select COLL_ACCESS_USER_ID where COLL_ACCESS_NAME = 'own' and COLL_NAME = '/nlmumc/projects/*project' ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;


        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';

        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;

            *displayName = ""
            foreach( *U in select META_USER_ATTR_VALUE where USER_ID = '*objectID' AND USER_TYPE = "rodsuser" and META_USER_ATTR_NAME == "displayName" ) {
                 *displayName = *U.META_USER_ATTR_VALUE
            }

            if (*displayName == "") {
                *displayName = *objectName
            }

            if ( *objectType == "rodsgroup" ) {
                msi_json_arrayops( *groups, *objectName, "add", *groupSize);
                *groupObject = '{ "groupName" : "*objectName", "groupId" : "*objectID" }';
                msi_json_arrayops( *groupObjects, *groupObject, "add", *groupObjectsSize );
            }

            if ( *objectType == "rodsuser" ) {
                msi_json_arrayops(*users, *objectName, "add", *userSize);
                *userObject = '{ "userName" : "*objectName", "userId" : "*objectID", "displayName" : "*displayName" }';
                msi_json_arrayops( *userObjects, *userObject, "add", *userObjectsSize );
            }
            # All other cases of objectType, such as "" or "rodsadmin", are skipped
        }
    }

    *result = '{"users": *users, "groups": *groups, "groupObjects": *groupObjects, "userObjects": *userObjects}';
}

INPUT *project=$"P000000001"
OUTPUT ruleExecOut
