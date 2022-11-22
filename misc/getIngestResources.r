# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/misc/getIngestResources.r

irule_dummy() {
    IRULE_getIngestResources(*result);
    writeLine("stdout", *result);
}

IRULE_getIngestResources(*result) {
    *resources = '[]';
    *resourcesSize = 0;

    foreach ( *Row in select RESC_NAME, RESC_COMMENT where RESC_VAULT_PATH = '/var/lib/irods/vault'  AND RESC_NAME != 'demoResc') {
        *name = *Row.RESC_NAME
        *comment = *Row.RESC_COMMENT
        *r = ' { "name": "*name", "comment": "*comment" } '
        msi_json_arrayops(*resources, *r, "add", *resourcesSize);
    }

    *result = *resources;
}

INPUT null
OUTPUT ruleExecOut
