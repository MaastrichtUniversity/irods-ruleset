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
                msi_json_arrayops(*users, *userObject, "add", *usersSize);
           } else if ( substr(*Row.USER_NAME, 0, 8) != "service-" ) {
                msi_json_arrayops(*users, *userObject, "add", *usersSize);
           }
        }
        else{
            msi_json_arrayops(*users, *userObject, "add", *usersSize);
        }
    }

    *result = *users;
}

INPUT *showServiceAccounts='true'
OUTPUT ruleExecOut