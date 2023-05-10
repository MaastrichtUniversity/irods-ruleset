#irule -F setTapeErrorAVU.r "*projectCollection='/nlmumc/projects/P000000001/C000000001'" "*initiator='jmelius'" "*attribute='attr'" "*value='val'" "*message='crash'"

irule_dummy() {
    IRULE_setTapeErrorAVU(*projectCollection, *initiator, *attribute, *value,*message);
}


IRULE_setTapeErrorAVU(*projectCollection, *initiator, *attribute, *value, *message) {
    msiAddKeyVal(*metaKV,  *attribute, *value);
    msiSetKeyValuePairsToObj(*metaKV, *projectCollection, "-C");
    msiWriteRodsLog("Tape archival/unarchival failed *projectCollection with error status '*value'", 0);

    uuChopPath(*projectCollection, *dir, *collectionID);
    uuChopPath(*dir, *dir2, *projectID);

    if (*value == "error-archive-failed"){
        *description = "Archival failed for collection *collectionID in project *projectID"
        submit_tape_error(*initiator, *description, *message)
    } else if (*value == "error-unarchive-failed"){
        *description = "Un-archival failed for collection *collectionID in project *projectID"
        submit_tape_error(*initiator, *description, *message)
    }

    failmsg(-1, "*message for *projectCollection");
}

INPUT *projectCollection='', *initiator='', *attribute='', *value='',*message=''
OUTPUT ruleExecOut
