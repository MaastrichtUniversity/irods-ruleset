# Call with
#
# irule -F getDataStewards.r

irule_dummy() {
    IRULE_getDataStewards(*result);
    writeLine("stdout", *result);
}

IRULE_getDataStewards(*result) {
    *users = '[]';
    *usersSize = 0;
    
    foreach (*Row in SELECT USER_NAME WHERE  META_USER_ATTR_VALUE == "data-steward" AND META_USER_ATTR_NAME == "specialty") {    		
        msi_json_arrayops(*users, *Row.USER_NAME, "add", *usersSize);
    }

    *result = *users;
}

INPUT null
OUTPUT ruleExecOut
