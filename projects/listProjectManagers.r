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

        *O = select USER_NAME, USER_TYPE, META_USER_ATTR_NAME, META_USER_ATTR_VALUE where USER_ID = '*objectID' AND USER_TYPE = "rodsuser";

        foreach (*R in *O) {
           *objectName = *R.USER_NAME;
           *objectType = *R.USER_TYPE;

           if ( *R.META_USER_ATTR_NAME == "displayName") {
               *value = *R.META_USER_ATTR_VALUE;
               msi_json_arrayops(*users, *objectName, "add", *userSize);
               *userObject = '{ "userName" : "*objectName", "userId" : "*objectID", "displayName" : "*value" }';
               msi_json_arrayops( *userObjects, *userObject, "add", *userObjectsSize );
           }
        }

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID' AND USER_TYPE = "rodsgroup";

        foreach (*R in *O) {
           *objectName = *R.USER_NAME;
           *objectType = *R.USER_TYPE;

           msi_json_arrayops( *groups, *objectName, "add", *groupSize);
           *groupObject = '{ "groupName" : "*objectName", "groupId" : "*objectID" }';
           msi_json_arrayops( *groupObjects, *groupObject, "add", *groupObjectsSize );
        }

        # All other cases of objectType, such as "" or "rodsadmin", are skipped
    }

    *result = '{"users": *users, "groups": *groups, "groupObjects": *groupObjects, "userObjects": *userObjects}';
}

INPUT *project=$"P000000001"
OUTPUT ruleExecOut
