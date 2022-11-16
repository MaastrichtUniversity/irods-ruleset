# Call with
# irule -F getResourceAVU.r "*resourceName='replRescUM01'" "*attribute='NCIT:C88193'" "*overrideValue=''" "*fatal='true'"
#
# The following arguments are optional when using irule -F,
# but still have to be specified when calling from within another rule:
# - *overrideValue (defaults to an empty string)
# - *fatal (defaults to 'true')


irule_dummy() {
    IRULE_getResourceAVU(*resourceName, *attribute, *value, *overrideValue, *fatal)
    writeLine("stdout", *value);
}


IRULE_getResourceAVU(*resourceName, *attribute, *value, *overrideValue, *fatal) {
    *value = "";
    foreach (*av in SELECT META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME == "*resourceName") {
        if ( *av.META_RESC_ATTR_NAME == *attribute) {
            *value = *av.META_RESC_ATTR_VALUE;
        }
    }
    if (*value == "") {
        if (*fatal == "true") {
            failmsg(-1, "ERROR: The attribute '*attribute' of resource '*resourceName' has no value in iCAT");
        } else {
            *value = *overrideValue;
        }
    }
}

INPUT *resourceName='', *attribute='', *value='', *overrideValue='', *fatal='true'
OUTPUT ruleExecOut
