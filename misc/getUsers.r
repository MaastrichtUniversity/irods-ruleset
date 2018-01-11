# Call with
#
# irule -F getUsers.r

irule_dummy() {
    IRULE_getUsers(*result);
    writeLine("stdout", *result);
}

IRULE_getUsers(*result) {
    *users = '[]';
    *usersSize = 0;

    foreach ( *Row in select USER_NAME where USER_TYPE = 'rodsuser') {
        msi_json_arrayops(*users, *Row.USER_NAME, "add", *usersSize);
    }

    *result = *users;
}

INPUT null
OUTPUT ruleExecOut