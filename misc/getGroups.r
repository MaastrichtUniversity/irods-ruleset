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

    foreach ( *Row in select USER_NAME, USER_ID where USER_TYPE = 'rodsgroup') {
        *objectName = *Row.USER_NAME;
        *objectID = *Row.USER_ID;
        *displayName = ""

        foreach( *U in select META_USER_ATTR_VALUE where USER_NAME = "*objectName" and META_USER_ATTR_NAME == "displayName" ) {
          *displayName = *U.META_USER_ATTR_VALUE
        }

        if (*displayName == "") {
          *displayName = *objectName
        }

        *groupObject = '{ "userName" : "*objectName", "userId" : "*objectID", "displayName" : "*displayName" }';

        if ( str(*showSpecialGroups) == "false" ) {
            if ( *Row.USER_NAME != "public" &&  *Row.USER_NAME != "rodsadmin" && *Row.USER_NAME != "DH-ingest" && *Row.USER_NAME != "DH-project-admins" ) {
                msi_json_arrayops(*groups, *groupObject, "add", *groupsSize);
            }
         } else {
            msi_json_arrayops(*groups, *groupObject, "add", *groupsSize);
         }
    }

    *result = *groups;
}

INPUT *showSpecialGroups='true'
OUTPUT ruleExecOut