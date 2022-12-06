# Call with
# irule -F getCollectionAVUTriple.r "*path='/nlmumc/ingest/zones/grieving-giant'" "*attribute='title'" "*overrideValue=''" "*fatal='true'"
#
# Return a JSON array with a triplet Attribute Value Unit for each matching input attribute to the collection
#
# The following arguments are optional when using irule -F,
# but still have to be specified when calling from within another rule:
# - *overrideValue (defaults to an empty string)
# - *fatal (defaults to 'true')


irule_dummy() {
    IRULE_getCollectionAVUTriple(*path, *attribute, *overrideValue, *fatal, *result)
    writeLine("stdout", *result );
}


IRULE_getCollectionAVUTriple(*path, *attribute, *overrideValue, *fatal, *result) {
    *value = "";
    *arrayops = '[]';
    *arraySize = 0;
    *result = '';
    foreach (*avu in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS WHERE COLL_NAME == "*path") {
        if ( *avu.META_COLL_ATTR_NAME == *attribute) {
            *value = *avu.META_COLL_ATTR_VALUE;
            *unit = *avu.META_COLL_ATTR_UNITS;
            *output = '{"attribute": "*attribute", "value": "*value", "unit": "*unit"}'
			msi_json_arrayops(*arrayops, *output, "add", *arraySize);
        }
    }
    *result = *arrayops;
    if (*arraySize == 0) {
        if (*fatal == "true") {
            failmsg(-1, "ERROR: The attribute '*attribute' of collection '*path' has no value in iCAT");
        } else {
            *result = *overrideValue;
            msiWriteRodsLog("WARNING: The attribute '*attribute' of collection '*path' has no value in iCAT. Using overrideValue '*overrideValue' instead",0);
        }
    }
}

INPUT *path='', *attribute='', *overrideValue='', *fatal='true'
OUTPUT ruleExecOut