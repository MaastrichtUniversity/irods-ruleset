# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/getDestinationResources.r

irule_dummy() {
    IRULE_getDestinationResources(*result);
    writeLine("stdout", *result);
}

IRULE_getDestinationResources(*result) {
    *resources = '[]';

    foreach ( *Row in select RESC_NAME, RESC_COMMENT where RESC_LOC = 'EMPTY_RESC_HOST' AND RESC_NAME != 'rootResc') {
        *name = *Row.RESC_NAME
        *comment = *Row.RESC_COMMENT
        *r = ' { "name": "*name", "comment": "*comment" } '
        json_arrayops_add(*resources, *r);
    }

    *result = *resources;
}

INPUT null
OUTPUT ruleExecOut
