#irule -F setTapeErrorAVU.r "*projectCollection='/nlmumc/projects/P000000001/C000000001'" "*attribute='attr'" "*value='val'" "*message='crash'"

irule_dummy() {
    IRULE_setTapeErrorAVU(*projectCollection, *attribute, *value,*message);
}


IRULE_setTapeErrorAVU(*projectCollection, *attribute, *value, *message) {
     msiAddKeyVal(*metaKV,  *attribute, *value);
     msiSetKeyValuePairsToObj(*metaKV, *projectCollection, "-C");
     msiWriteRodsLog("Tape archival/unarchival failed *projectCollection with error status '*value'", 0);
     failmsg(-1, "*message for *projectCollection");
}

INPUT *projectCollection='', *attribute='', *value='',*message=''
OUTPUT ruleExecOut
