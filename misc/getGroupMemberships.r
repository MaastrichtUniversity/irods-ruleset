# Call with
#
# irule -F getGroupMemberships.r "*user='name'" (where name is like name@maastrichtuniversity.nl

irule_dummy() {
    IRULE_getGroupMemberships(*user, *groupList);
}

IRULE_getGroupMemberships(*user, *groupList) {
	userNameToUserId(*user, *userId);
	
	*groups = "";
	foreach (*row in SELECT USER_GROUP_NAME, USER_GROUP_ID
				WHERE USER_ID = '*userId') {
		msiGetValByKey(*row,"USER_GROUP_NAME",*group);
		# workasround needed: iRODS returns username also as a group !!
		if (*group != *user) {
			*groups = "*groups:*group";
		}
	}
	*groups = triml(*groups,":");
	*groupList = split(*groups, ":");

	writeLine("stdout", "*groupList");

}

INPUT *user='rods'
OUTPUT ruleExecOut
