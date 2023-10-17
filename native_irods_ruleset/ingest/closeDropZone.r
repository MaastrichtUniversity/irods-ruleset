# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/ingest/closeDropZone.r "*token='bla-token'"
#
# This is also an OPS rule for "SOP_Beheer [iRODS] Remove dropzone"

irule_dummy() {
    IRULE_closeDropZone(*token)
}

IRULE_closeDropZone(*token) {
    *srcColl = "";
    *dropzoneType = "";

    # Check if the dropzone exists
    *mountedPath = "/nlmumc/ingest/zones/*token";
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_NAME == *mountedPath) {
        *srcColl = *Row.COLL_NAME;
        *dropzoneType = "mounted";
    }

    *directPath = "/nlmumc/ingest/direct/*token"
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_NAME == *directPath) {
        *srcColl = *Row.COLL_NAME;
        *dropzoneType = "direct";
    }

    if ( *srcColl == "" ) {
        # -814000 CAT_UNKNOWN_COLLECTION
        msiExit("-814000", "Unknown dropzone *token");
    }

    getCollectionAVU(*srcColl, "project", *project, "", "true");
    getCollectionAVU("/nlmumc/projects/*project", "ingestResource", *ingestResource, "", "true");

    # Obtain the resource host from the specified ingest resource
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
        *ingestResourceHost = *r.RESC_LOC;
    }

    *directIngestResourceHost = "";
    get_direct_ingest_resource_host(*directIngestResourceHost);
    msiWriteRodsLog("INFO: Closing dropzone *token from project *project on direct resource host *directIngestResourceHost", 0);

    if (*dropzoneType == "mounted") {
        getCollectionAVU(*srcColl, "legacy", *legacyDropzone, "false", "false")
        msiWriteRodsLog("DEBUG: *srcColl is a legacy dropzone: *legacyDropzone", 0)

        if (*legacyDropzone == "true") {
            # The unmounting of the physical mount point is not done in the delay() where msiRmColl on the token
            # is done.
            # This is because of a bug in the unmount. This is kept in memory for
            # the remaining of the irodsagent session.
            # See also: https://groups.google.com/d/msg/irod-chat/rasDT-AGAVQ/Bb31VJ9SAgAJ
            *codeUnmount = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));
            if ( *codeUnmount < 0 ) {
                msiWriteRodsLog("ERROR: msiPhyPathReg failed for *srcColl", 0);
            }
        }
    }

    delay("<PLUSET>1s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        *error = errorcode(msiRmColl(*srcColl, "forceFlag=", *OUT));
        if ( *error < 0 ) {
            msiWriteRodsLog("Error: Failed to remove Dropzone-collection: *srcColl", 0);
        }

        # Disabling the network mounted ingest zone needs to be executed on remote ires server
        if ( *dropzoneType == "mounted" ){
            msiWriteRodsLog("INFO: Closing dropzone *token from project *project on ingest resource host *ingestResourceHost", 0);
            remote(*ingestResourceHost, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
              msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *ExecOUT);
            }
        }

        remote(*directIngestResourceHost, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
           # Only the metadata files exist on stagingResc01 and need to be deleted
           if ( *dropzoneType == "mounted" ){
              msiExecCmd("disable-ingest-zone.sh", "/mnt/stagingResc01/ingest/zones/" ++ *token, "null", "null", "null", *ExecOUT);
           }
           # Disabling the ingest zone needs to be executed on remote ires server
           else if ( *dropzoneType == "direct" ){
              msiExecCmd("disable-ingest-zone.sh", "/mnt/stagingResc01/ingest/direct/" ++ *token, "null", "null", "null", *ExecOUT);
           }
        }
    }
}

INPUT *token=''
OUTPUT ruleExecOut