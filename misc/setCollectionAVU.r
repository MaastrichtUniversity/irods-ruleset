# Call with
#
# irule -F setCollectionAVU.r "*collection='/nlmumc/projects/P000000001'" "*attribute='attr'" "*value='val'"

irule_dummy() {
    IRULE_setCollectionAVU(*collection, *attribute, *value);
}


IRULE_setCollectionAVU(*collection, *attribute, *value) {
     msiAddKeyVal(*metaKV,  *attribute, *value);
     msiSetKeyValuePairsToObj(*metaKV, *collection, "-C");
     msiWriteRodsLog("INFO: *collection: Setting '*attribute' to '*value'", 0);
}

INPUT *collection='', *attribute='', *value=''
OUTPUT ruleExecOut