# Call with
#
# irule -F listProjectContributors.r "*project='P000000001'" "*inherited='true'"
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

    *groupName2Ids = '[]';
    *groupName2IdsSize = 0;

    if ( *inherited == "true" ) {
        *criteria = "'own', 'modify object'"
    } else {
        *criteria = "'modify object'"
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
            msi_json_arrayops( *groups, *objectName, "add", *groupSize);
            *groupName2Id = '{ "groupName" : "*objectName", "groupId" : "*objectID" }';
            msi_json_arrayops( *groupName2Ids, *groupName2Id, "add", *groupName2IdsSize );
        }

        if ( *objectType == "rodsuser" ) {
            msi_json_arrayops(*users, *objectName, "add", *userSize);
        }

        # All other cases of objectType, such as "" or "rodsadmin", are skipped
    }

    *result = '{"users": *users, "groups": *groups, "groupName2Ids": *groupName2Ids }';
}

INPUT *project=$"P00000001", *inherited=""
OUTPUT ruleExecOut
