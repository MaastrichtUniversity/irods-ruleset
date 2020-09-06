# Call with
#
# irule -F getGroupMemberships.r "*showSpecialGroups='true'" "*userName='name'" (where name is like name@maastrichtuniversity.nl

irule_dummy() {
    IRULE_getGroupMemberships(*showSpecialGroups, *userName, *result);
    writeLine("stdout", *result);
}

IRULE_getGroupMemberships(*showSpecialGroups, *userName, *result) {
    *userId = "";
    #userNameToUserId(*userName, *userId);
    #writeLine("serverLog", "getting groupMemberships for userName: *user, userId: *userId" );
    *result = '[]';
    *resultSize = 0;
    foreach (*row in SELECT order(USER_GROUP_NAME), USER_GROUP_ID
                     WHERE USER_TYPE = 'rodsgroup'   
                     #WHERE USER_ID = '*userId'
    ) {
          *groupName = *row.USER_GROUP_NAME;
          *groupId = *row.USER_GROUP_ID;
          *groupDisplayName = *groupName
          *groupDescription = ""
          # workaround needed: iRODS returns username also as a group !!
          if (*groupName != *userName) {
             #get AVU-values
             foreach (*av in SELECT META_USER_ATTR_NAME, META_USER_ATTR_VALUE, USER_GROUP_ID, USER_GROUP_NAME where USER_TYPE = 'rodsgroup' and USER_GROUP_ID = *groupId ) {
                if( "displayName" == *av.META_USER_ATTR_NAME ) {
                   *groupDisplayName = *av.META_USER_ATTR_VALUE
                }
                else if( "description" == *av.META_USER_ATTR_NAME ) {
                   *groupDescription = *av.META_USER_ATTR_VALUE
                } 
             }
     
             *groupJSON = '{ "groupId": "*groupId", "name" : "*groupName", "displayName" : "*groupDisplayName", "description" : "*groupDescription" }';
             if ( str(*showSpecialGroups) == "false" ) {     
                if ( *row.USER_GROUP_NAME != "public" &&  *row.USER_GROUP_NAME != "rodsadmin" && *row.USER_GROUP_NAME != "DH-ingest" && *row.USER_GROUP_NAME != "DH-project-admins" ) {
                   msi_json_arrayops( *result, *groupJSON, "add", *resultSize);
                }
             }
             else {
                msi_json_arrayops( *result, *groupJSON, "add", *resultSize);
             }
          }
    }
}

INPUT *showSpecialGroups='false', *userName='rods'
OUTPUT ruleExecOut
