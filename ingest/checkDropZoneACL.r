# This rule checks if a user has sufficient permissions to (create and) delete dropzones, based on iRODS ACL's on the dropzones parent-collection
#
# irule -F checkDropZoneACL.r

irule_dummy() {
    IRULE_checkDropZoneACL(*user, *result)
    #writeLine("stdout", *result);
}

IRULE_checkDropZoneACL(*user, *result) {
    *result = "";

    userNameToUserId(*user, *userId);

    # Create a list of group-IDs (the user-ID is also a "group-ID")
    *groups = '';
    foreach ( *Row2 in SELECT USER_GROUP_ID where USER_ID = *userId ) {
         *groupID = "'" ++ *Row2.USER_GROUP_ID ++ "'";
         *groups= *groups ++ "," ++ *groupID;
    }

    # Remove first comma
    *groups=substr(*groups, 1, strlen(*groups));

    # Generate and execute SQL query
    msiMakeGenQuery("count(COLL_NAME)", "COLL_NAME = '/nlmumc/ingest/zones' and COLL_ACCESS_NAME in ('own', 'modify object') and COLL_ACCESS_USER_ID in (*groups)", *Query);
    msiExecGenQuery(*Query, *QOut);

    # Check if SQL result was not empty and return true
    foreach ( *Row in *QOut ) {
        if ( int(*Row.COLL_NAME) > 0 ) {
            *result= "true";
            #writeLine("stdout", "true");
        } else {
            *result= "false";
            #writeLine("stdout", "false");
        }
    }

}

INPUT *user='',*result=''
OUTPUT ruleExecOut