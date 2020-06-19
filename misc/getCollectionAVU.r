# Call with
# irule -F getCollectionAVU.r "*collName='/nlmumc/ingest/zones/grieving-giant'" "*attribute='title'" "*overrideValue=''" "*fatal='true'"
#
# The following arguments are optional when using irule -F,
# but still have to be specified when calling from within another rule:
# - *overrideValue (defaults to an empty string)
# - *fatal (defaults to 'true')


irule_dummy() {
    IRULE_getCollectionAVU(*collName, *attribute, *value, *overrideValue, *fatal)
    writeLine("stdout", *value);
}


IRULE_getCollectionAVU(*collName, *attribute, *value, *overrideValue, *fatal) {
    *value = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*collName") {
        if ( *av.META_COLL_ATTR_NAME == *attribute) {
            *value = *av.META_COLL_ATTR_VALUE;
        }
    }
    if (*value == "") {
        if (*fatal == "true") {
            failmsg(-1, "ERROR: The attribute '*attribute' of collection '*collName' has no value in iCAT");
        } else {
            *value = *overrideValue;
        }
    }
}

INPUT *collName='', *attribute='', *value='', *overrideValue='', *fatal='true'
OUTPUT ruleExecOut