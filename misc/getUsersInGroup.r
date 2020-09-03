# Call with
#
# irule -F getUsersInGroup.r "*groupId='2'"

irule_dummy() {
    IRULE_getUsersInGroup(*groupId, *result);
    writeLine("stdout", *result);
}

IRULE_getUsersInGroup(*groupId, *result) {
 #   writeLine("serverLog", "searching users in group: *group");	
    *result = "[]";
    *resultSize = 0;
    foreach ( *Row in select order(USER_NAME), USER_ID where USER_TYPE = 'rodsuser' and USER_GROUP_ID = *groupId ) {
        *objectName = *Row.USER_NAME;
        *objectID = *Row.USER_ID;
        *displayName = ""

        foreach( *U in select META_USER_ATTR_VALUE where USER_NAME = "*objectName" and META_USER_ATTR_NAME == "displayName" ) {
          *displayName = *U.META_USER_ATTR_VALUE
        }

        if (*displayName == "") {
          *displayName = *objectName
        }

        *userObject = '{ "userName" : "*objectName", "userId" : "*objectID", "displayName" : "*displayName" }';
        msi_json_arrayops(*result, *userObject, "add", *resultSize);
    }
}


INPUT *groupId=''
OUTPUT ruleExecOut
