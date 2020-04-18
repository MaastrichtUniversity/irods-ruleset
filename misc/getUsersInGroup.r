# Call with
#
# irule -F getUsersInGroup.r "*group='name'"

irule_dummy() {
    IRULE_getUsersInGroup(*groupId, *result);
    writeLine("stdout", *result);
}

IRULE_getUsersInGroup(*groupId, *result) {
 #   writeLine("serverLog", "searching users in group: *group");	
    *result = "[]";
    *resultSize = 0;
    foreach ( *row in select order(USER_NAME), USER_ID where USER_TYPE = 'rodsuser' and USER_GROUP_ID = *groupId ) {
        *displayName = *row.USER_NAME;
        *userId = *row.USER_ID;
        *userJSON = '{ "userId": "*userId", "displayName" : "*displayName" }';
        msi_json_arrayops(*result, *userJSON, "add", *resultSize);
    }
}


INPUT *groupId=''
OUTPUT ruleExecOut
