# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getGroups.r "*showSpecialGroups='true'"

irule_dummy() {
    IRULE_getGroups(*showSpecialGroups, *result);
    writeLine("stdout", *result);
}

IRULE_getGroups(*showSpecialGroups, *result) {
    *groups = '[]';

    foreach ( *Row in select USER_NAME, USER_ID where USER_TYPE = 'rodsgroup') {
        *objectName = *Row.USER_NAME;
        *objectID = *Row.USER_ID;
        *displayName = *objectName;
        *description = "";

        foreach (*av in SELECT META_USER_ATTR_NAME, META_USER_ATTR_VALUE, USER_GROUP_ID, USER_GROUP_NAME where USER_TYPE = 'rodsgroup' and USER_GROUP_ID = *objectID ) {
           if( "displayName" == *av.META_USER_ATTR_NAME ) {
              *displayName = *av.META_USER_ATTR_VALUE;
           }
           else if( "description" == *av.META_USER_ATTR_NAME ) {
              *description = *av.META_USER_ATTR_VALUE;
           } 
        }

        *groupObject = '{ "userName" : "*objectName", "userId" : "*objectID", "displayName" : "*displayName", "description" : "*description" }';

        if ( str(*showSpecialGroups) == "false" ) {
            if ( *Row.USER_NAME != "public" &&  *Row.USER_NAME != "rodsadmin" && *Row.USER_NAME != "DH-ingest" && *Row.USER_NAME != "DH-project-admins" ) {
                json_arrayops_add(*groups, *groupObject, "");
            }
         } else {
            json_arrayops_add(*groups, *groupObject, "");
         }
    }

    *result = *groups;
}

INPUT *showSpecialGroups='true'
OUTPUT ruleExecOut
