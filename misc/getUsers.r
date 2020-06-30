# Call with
#
# irule -F getUsers.r "*showServiceAccounts='true'"

irule_dummy() {
    IRULE_getUsers(*showServiceAccounts , *result);
    writeLine("stdout", *result);
}

IRULE_getUsers(*showServiceAccounts,*result) {
    *users = '[]';
    *usersSize = 0;

    foreach ( *Row in select USER_NAME where USER_TYPE = 'rodsuser') {
         if ( str(*showServiceAccounts) == "false" ) {
               if ( strlen(*Row.USER_NAME) < 8 ) {
                    msi_json_arrayops(*users, *Row.USER_NAME, "add", *usersSize);
               } else if ( substr(*Row.USER_NAME, 0, 8) != "service-" ) {
                    msi_json_arrayops(*users, *Row.USER_NAME, "add", *usersSize);
               }
         }
         else{
            msi_json_arrayops(*users, *Row.USER_NAME, "add", *usersSize);
         }
    }

    *result = *users;
}

INPUT *showServiceAccounts='true'
OUTPUT ruleExecOut