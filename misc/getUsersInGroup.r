# Call with
#
# irule -F getUsersInGroup.r "*group='name'"

irule_dummy() {
    IRULE_getUsersInGroup(*group, *result);
}

IRULE_getUsersInGroup(*group, *result) {
#	groupNameToGroupId(*group, *groupId);
        writeLine("serverLog", "searching users in group: *group");
	
	*users = "";
        foreach ( *row in select USER_NAME where USER_TYPE = 'rodsuser' and USER_GROUP_NAME = *group ) {
           msiGetValByKey(*row,"USER_NAME",*user);
           *users = "*users:*user";
	}
	*users = triml(*users,":");
	*userList = split(*users, ":");

	writeLine("serverLog", "found users: *userList");

        *result = *userList;
}


INPUT *group=''
OUTPUT ruleExecOut
