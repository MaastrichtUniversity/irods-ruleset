# Call with
#
# irule -F getUsersInGroup.r "*group='name'"

irule_dummy() {
    IRULE_getUsersInGroup(*group, *result);
    writeLine("stdout", *result);
}

IRULE_getUsersInGroup(*group, *result) {
        writeLine("serverLog", "searching users in group: *group");
	
	*users = "[]";
        *usersSize = 0;
        foreach ( *row in select USER_NAME where USER_TYPE = 'rodsuser' and USER_GROUP_NAME = *group ) {
           msiGetValByKey(*row,"USER_NAME",*user);
           msi_json_arrayops(*users, *user, "add", *usersSize);
	}
        *result = *users;

	writeLine("serverLog", "found users: *result");
}


INPUT *group=''
OUTPUT ruleExecOut
