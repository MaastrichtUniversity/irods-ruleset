# Call with
#
# irule -F getDataStewards.r

irule_dummy() {
    IRULE_getDataStewards(*result);
    writeLine("stdout", *result);
}

IRULE_getDataStewards(*result) {
    *userObjects = '[]';
    *userObjectsSize = 0;

    *users = ""
    foreach (*Row in SELECT USER_ID WHERE META_USER_ATTR_VALUE == "data-steward" AND META_USER_ATTR_NAME == "specialty") {
        *userID = *Row.USER_ID;

        # The GenQuery expect the user id to be quoted
        if (*users == ""){
            *users = "'" ++ *userID  ++ "'"
        }
        else{
            *users = *users ++ ", '" ++ *userID ++ "'";
        }
    }
    msiMakeGenQuery("USER_NAME, USER_ID, META_USER_ATTR_VALUE", "USER_ID in (*users)", *Query);
    msiExecGenQuery(*Query, *QOut);
    foreach ( *O in *QOut ) {
        *userName = *O.USER_NAME;
        *userID = *O.USER_ID;

        *displayName = *userName;
        foreach (*Row in SELECT META_USER_ATTR_VALUE WHERE USER_NAME == "*userName" AND META_USER_ATTR_NAME == "displayName") {
            *displayName = *Row.META_USER_ATTR_VALUE;
        }
        *userObject = '{ "userName" : "*userName", "userId" : "*userID", "displayName" : "*displayName" }';
        msi_json_arrayops( *userObjects, *userObject, "add", *userObjectsSize );
	}
    *result = *userObjects;
}

INPUT null
OUTPUT ruleExecOut
