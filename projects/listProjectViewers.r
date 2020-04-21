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

    if ( *inherited == "true" ) {
        *criteria = "'own', 'modify object', 'read object'"
    } else {
        *criteria = "'read object'"
    }

    msiMakeGenQuery("COLL_ACCESS_USER_ID", "COLL_ACCESS_NAME in (*criteria)  and COLL_NAME = '/nlmumc/projects/*project'", *Query);
    msiExecGenQuery(*Query, *QOut);

    foreach ( *Row in *QOut ) {
        *objectID = *Row.COLL_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';

        *objectName = "";
        *objectType = "";

        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        if ( *objectType == "rodsgroup" ) {
            msi_json_arrayops(*groups, *objectName, "add", *groupSize);
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

INPUT *project=$"P000000001",*inherited=""
OUTPUT ruleExecOut
