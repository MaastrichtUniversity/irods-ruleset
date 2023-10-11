# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getUsers.r "*showServiceAccounts='true'"

irule_dummy() {
    IRULE_getUsers(*showServiceAccounts , *result);
    writeLine("stdout", *result);
}

IRULE_getUsers(*showServiceAccounts,*result) {
    *users = '[]';

    foreach ( *Row in select USER_NAME, USER_ID where USER_TYPE = 'rodsuser') {
        *objectName = *Row.USER_NAME;
        *objectID = *Row.USER_ID;
        *displayName = ""

        foreach( *U in select META_USER_ATTR_VALUE where USER_NAME = "*objectName" and META_USER_ATTR_NAME == "displayName" ) {
            *displayName = *U.META_USER_ATTR_VALUE
        }

        if (*displayName == "") {
            *displayName = *objectName
        }

        *userObject = '{ "userName" : "*objectName", "userId" : "*objectID", "displayName" : "*displayName" }';

        if ( str(*showServiceAccounts) == "false" ) {
           if ( strlen(*Row.USER_NAME) < 8 ) {
                json_arrayops_add(*users, *userObject);
           } else if ( substr(*Row.USER_NAME, 0, 8) != "service-" ) {
                json_arrayops_add(*users, *userObject);
           }
        }
        else{
            json_arrayops_add(*users, *userObject);
        }
    }

    *result = *users;
}

INPUT *showServiceAccounts='true'
OUTPUT ruleExecOut
