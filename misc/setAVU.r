# Call with
#
# irule -F setAVU.r "*collection='/nlmumc/projects/P000000001'" "*attribute='attr'" "*value='val'" "*unit='unit'"

irule_dummy() {
    IRULE_setAVU(*type, *path, *attribute, *value, *unit);
}


IRULE_setAVU(*type, *path, *attribute, *value, *unit) {
     msi_add_avu(*type, *path, *attribute, *value, *unit)
     msiWriteRodsLog("Setting '*attribute' for *path to *value at *unit", 0);
}

INPUT *type='', *path='', *attribute='', *value='', *unit=''
OUTPUT ruleExecOut