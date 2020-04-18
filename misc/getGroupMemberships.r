# Call with
#
# irule -F getGroupMemberships.r "*user='name'" (where name is like name@maastrichtuniversity.nl

irule_dummy() {
    IRULE_getGroupMemberships(*user, *result);
    writeLine("stdout", *result);
}

IRULE_getGroupMemberships(*userName, *result) {
    *userId = "";
    #userNameToUserId(*userName, *userId);
    #writeLine("serverLog", "getting groupMemberships for userName: *user, userId: *userId" );
    *result = '[]';
    *resultSize = 0;
    foreach (*row in SELECT order(USER_GROUP_NAME), USER_GROUP_ID
                     WHERE USER_TYPE = 'rodsgroup'   
                     #WHERE USER_ID = '*userId'
    ) { 
       if ( *row.USER_GROUP_NAME != "public" &&  *row.USER_GROUP_NAME != "rodsadmin" && *row.USER_GROUP_NAME != "DH-ingest" && *row.USER_GROUP_NAME != "DH-project-admins" ) {
          *groupName = *row.USER_GROUP_NAME;
          *groupId = *row.USER_GROUP_ID;
          # workasround needed: iRODS returns username also as a group !!
          if (*groupName != *userName) {
             *groupJSON = '{ "groupId": "*groupId", "name" : "*groupName" }';
              msi_json_arrayops( *result, *groupJSON, "add", *resultSize);
          }
       }
    }
}

INPUT *user='rods'
OUTPUT ruleExecOut
