# Call with
#
# irule -F getGroupMemberships.r "*user='name'" (where name is like name@maastrichtuniversity.nl

irule_dummy() {
    IRULE_getGroupMemberships(*user, *result);
}

IRULE_getGroupMemberships(*user, *result) {
        *userId = "";
	userNameToUserId(*user, *userId);
	writeLine("serverLog", "getting groupMemberships for userName: *user, userId: *userId" );
	*groups = '[]';
        *groupsSize = 0;
	foreach (*row in SELECT USER_GROUP_NAME, USER_GROUP_ID
				WHERE USER_ID = '*userId' ) {
                if ( *row.USER_GROUP_NAME != "public" &&  *row.USER_GROUP_NAME != "rodsadmin" && *row.USER_GROUP_NAME != "DH-ingest" && *row.USER_GROUP_NAME != "DH-project-admins" ) {
		   msiGetValByKey(*row,"USER_GROUP_NAME",*group);
		   # workasround needed: iRODS returns username also as a group !!
		   if (*group != *user) {
                      #*groups = "*groups:*group";
                      msi_json_arrayops(*groups, *group, "add", *groupsSize); 
                   }
		}
	}
	#*groups = triml(*groups,":");
	#*result = split(*groups, ":");
        *result = *groups;
	writeLine("serverLog", "user is member of: *result");
}

INPUT *user='rods'
OUTPUT ruleExecOut
