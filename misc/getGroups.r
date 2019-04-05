# Call with
#
# irule -F getGroups.r "*showSpecialGroups='true'"

irule_dummy() {
    IRULE_getGroups(*showSpecialGroups, *result);
    writeLine("stdout", *result);
}

IRULE_getGroups(*showSpecialGroups, *result) {
    *groups = '[]';
    *groupsSize = 0;

    foreach ( *Row in select USER_NAME where USER_TYPE = 'rodsgroup') {
    		 if ( str(*showSpecialGroups) == "false" ) {
    		 			if ( *Row.USER_NAME != "public" &&  *Row.USER_NAME != "rodsadmin"
    		 					&&  *Row.USER_NAME != "DH-ingest" &&  *Row.USER_NAME != "DH-project-admins") {
                      msi_json_arrayops(*groups, *Row.USER_NAME, "add", *groupsSize);
               }             
         }
         else{
            msi_json_arrayops(*groups, *Row.USER_NAME, "add", *groupsSize);
         }
    }

    *result = *groups;
}

INPUT *showSpecialGroups='true'
OUTPUT ruleExecOut