# Call with
#
# irule -F listProjectViewers.r "*project='P000000001'" "*inherited='true'"
#
# Role inheritance
# *inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
# *inherited='false' only shows explicit contributors. i.e. A contributor only has WRITE access


irule_dummy() {
    IRULE_listProjectViewers(*project, *inherited, *result);

    writeLine("stdout", *result);
}

IRULE_listProjectViewers(*project, *inherited, *result) {
    *groups = '[]';
    *groupSize = 0;

    *users = '[]';
    *userSize = 0;

    *groupObjects = '[]';
    *groupObjectsSize = 0;

    *userObjects = '[]';
    *userObjectsSize = 0;

    if ( *inherited == "true" ) {
        *criteria = "'own', 'modify_object', 'read_object'"
    } else {
        *criteria = "'read_object'"
    }

    msiMakeGenQuery("COLL_ACCESS_USER_ID", "COLL_ACCESS_NAME in (*criteria)  and COLL_NAME = '/nlmumc/projects/*project'", *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach ( *Row in *QOut ) {
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
                     *description = *av.META_USER_ATTR_VALUE;
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

INPUT *project=$"P000000001",*inherited=""
OUTPUT ruleExecOut
