# Call with
#
# irule -F listProjectContributors.r "*project='P000000010'" "*inherited='true'"
#
# Role inheritance
# *inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
# *inherited='false' only shows explicit contributors. i.e. A contributor only has WRITE access


irule_dummy() {
    IRULE_listProjectContributors(*project, *inherited, *result);

    writeLine("stdout", *result);
}

IRULE_listProjectContributors(*project, *inherited, *result) {
    *groups = '[]';
    *groupSize = 0;

    *users = '[]';
    *userSize = 0;

    *groupObjects = '[]';
    *groupObjectsSize = 0;

    *userObjects = '[]';
    *userObjectsSize = 0;

    if ( *inherited == "true" ) {
        *criteria = "'own', 'modify object'"
    } else {
        *criteria = "'modify object'"
    }

    msiMakeGenQuery("COLL_ACCESS_USER_ID", "COLL_ACCESS_NAME in (*criteria)  and COLL_NAME = '/nlmumc/projects/*project'", *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach ( *Row in *QOut ) {
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

INPUT *project=$"P00000001", *inherited=""
OUTPUT ruleExecOut
