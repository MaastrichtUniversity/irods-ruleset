# Call with
# irule -F queryAVU.r "*collName='/nlmumc/ingest/zones/grieving-giant'" "*attribute='title'"

irule_dummy() {
    IRULE_queryAVU(*collName, *attribute, *value)
    writeLine("stdout", *value);
}


IRULE_queryAVU(*collName, *attribute, *value) {
    *output = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*collName") {
        if ( *av.META_COLL_ATTR_NAME == *attribute) {
            *value = *av.META_COLL_ATTR_VALUE;
        }
    }
}

INPUT *collName='', *attribute='', *value=''
OUTPUT ruleExecOut