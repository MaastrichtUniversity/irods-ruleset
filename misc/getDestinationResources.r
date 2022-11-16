# Call with
#
# irule -F /rules/misc/getDestinationResources.r

irule_dummy() {
    IRULE_getDestinationResources(*result);
    writeLine("stdout", *result);
}

IRULE_getDestinationResources(*result) {
    *resources = '[]';
    *resourcesSize = 0;

    foreach ( *Row in select RESC_NAME, RESC_COMMENT where RESC_LOC = 'EMPTY_RESC_HOST' AND RESC_NAME != 'rootResc') {
        *name = *Row.RESC_NAME
        *comment = *Row.RESC_COMMENT
        *r = ' { "name": "*name", "comment": "*comment" } '
        msi_json_arrayops(*resources, *r, "add", *resourcesSize);
    }

    *result = *resources;
}

INPUT null
OUTPUT ruleExecOut
