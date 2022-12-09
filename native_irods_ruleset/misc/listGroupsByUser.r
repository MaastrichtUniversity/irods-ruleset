# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/listGroupsByUser.r | python -m json.tool

irule_dummy() {
    IRULE_listGroupsByUser(*result);
    writeLine("stdout", *result);
}

IRULE_listGroupsByUser(*result) {
    *result = '[]';
    *size2 = 0;
    foreach ( *Row in SELECT USER_NAME, USER_ID WHERE USER_TYPE ='rodsgroup' ) {
       *groups = '';
       *json_str = '[]';
       *size = 0;
       *groupName = *Row.USER_NAME;
       *groupID = *Row.USER_ID;
       #User rodsadmin crashes rest of scripts
       if (*groupName != 'rodsadmin') {
            # Query the users inside the current *groupName and add its display name in *json_str
            foreach ( *Row2 in SELECT USER_NAME, META_USER_ATTR_VALUE where USER_GROUP_NAME  = *groupName AND USER_NAME != *groupName AND META_USER_ATTR_NAME = 'displayName' ) {
                 msi_json_arrayops(*json_str, *Row2.META_USER_ATTR_VALUE, "add", *size);
            }
            *displayName = *groupName;
            *description = "";
            # Query the display name and description for the current *groupID
            foreach (*av in SELECT META_USER_ATTR_NAME, META_USER_ATTR_VALUE where USER_TYPE = 'rodsgroup' and USER_GROUP_ID = '*groupID' ) {
               if( "displayName" == *av.META_USER_ATTR_NAME ) {
                  *displayName = *av.META_USER_ATTR_VALUE;
               }
               else if( "description" == *av.META_USER_ATTR_NAME ) {
                  *description = *av.META_USER_ATTR_VALUE;
               }
            }

            *details = '{ "GroupName": "*groupName", "DisplayName": "*displayName", "Description": "*description", "Users": *json_str}';
            msi_json_arrayops(*result,  *details, "add", *size2);
       }
    }
}

INPUT *result=''
OUTPUT ruleExecOut
