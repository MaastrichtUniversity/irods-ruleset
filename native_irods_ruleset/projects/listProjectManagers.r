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
            *displayName = *objectName;
            *description = "";

            if ( *objectType == "rodsgroup" ) {                
                foreach (*av in SELECT META_USER_ATTR_NAME, META_USER_ATTR_VALUE, USER_GROUP_ID, USER_GROUP_NAME where USER_TYPE = 'rodsgroup' and USER_GROUP_ID = *objectID ) {
                  if( "displayName" == *av.META_USER_ATTR_NAME ) {
                     *displayName = *av.META_USER_ATTR_VALUE;
                  }
                  else if( "description" == *av.META_USER_ATTR_NAME ) {
                     *description = *av.META_USER_ATTR_VALUE
                  } 
                }
                msi_json_arrayops( *groups, *objectName, "add", *groupSize);
                *groupObject = '{ "groupName" : "*objectName", "groupId" : "*objectID", "displayName" : "*displayName", "description" : "*description" }';
                msi_json_arrayops( *groupObjects, *groupObject, "add", *groupObjectsSize );
            }

            if ( *objectType == "rodsuser" ) {
                foreach( *U in select META_USER_ATTR_VALUE where USER_ID = '*objectID' AND USER_TYPE = "rodsuser" and META_USER_ATTR_NAME == "displayName" ) {
                   *displayName = *U.META_USER_ATTR_VALUE;
                }
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
