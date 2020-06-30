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
    
    foreach (*Row in SELECT USER_ID WHERE  META_USER_ATTR_VALUE == "data-steward" AND META_USER_ATTR_NAME == "specialty") {
        *userID = *Row.USER_ID;

        foreach (*O in SELECT USER_NAME, META_USER_ATTR_VALUE WHERE USER_ID == "*userID" AND META_USER_ATTR_NAME == "displayName") {
            *userName = *O.USER_NAME;
            *value = *O.META_USER_ATTR_VALUE;

            *userObject = '{ "userName" : "*userName", "userId" : "*userID", "displayName" : "*value" }';
            msi_json_arrayops( *userObjects, *userObject, "add", *userObjectsSize );
        }
    }

    *result = *userObjects;
}

INPUT null
OUTPUT ruleExecOut
