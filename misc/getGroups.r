# Call with
#
# irule -F getGroups.r

irule_dummy() {
    IRULE_getGroups(*result);
    writeLine("stdout", *result);
}

IRULE_getGroups(*result) {
    *groups = '[]';
    *groupsSize = 0;

    foreach ( *Row in select USER_NAME where USER_TYPE = 'rodsgroup') {
        msi_json_arrayops(*groups, *Row.USER_NAME, "add", *groupsSize);
    }

    *result = *groups;
}

INPUT null
OUTPUT ruleExecOut