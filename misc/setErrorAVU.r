#irule -F setErrorAVU.r irule -F setErrorAVU.r "*collection='/nlmumc/home/rods'" "*attribute='attr'" "*value='val'" "*message='crash'"

irule_dummy() {
    IRULE_setErrorAVU(*collection, *attribute, *value,*message);
}


IRULE_setErrorAVU(*collection, *attribute, *value,*message) {    
     msiAddKeyVal(*metaKV,  *attribute, *value);
     msiSetKeyValuePairsToObj(*metaKV, *collection, "-C");
     msiWriteRodsLog("Ingest failed of *collection with error status '*value'", 0);
     msiWriteRodsLog(*message, 0);
     failmsg(0, "*message for *collection");
}

INPUT *collection='', *attribute='', *value='',*message=''
OUTPUT ruleExecOut
