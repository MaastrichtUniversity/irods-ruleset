# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within post_ingest.py rule

delayRemoveDropzone(*srcColl, *ingestResourceHost, *token, *dropzoneType) {
     *irodsIngestRemoveDelay = ""
     get_env("IRODS_INGEST_REMOVE_DELAY", "true", *irodsIngestRemoveDelay)

     delay("<PLUSET>*irodsIngestRemoveDelay</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        *error = errorcode(msiRmColl(*srcColl, "forceFlag=", *OUT));
        if ( *error < 0 ) {
            # Only log the following lines for elastalert
            msiWriteRodsLog("Ingest failed of *srcColl with error status 'error-post-ingestion'", 0);
            msiWriteRodsLog("Error removing Dropzone-collection", 0);
        }

        # Disabling the network mounted ingest zone needs to be executed on remote ires server
        if ( *dropzoneType == "mounted" ){
            remote(*ingestResourceHost,"") {
              msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
            }
        }
        *directIngestResourceHost = "";
        get_direct_ingest_resource_host(*directIngestResourceHost);
        remote(*directIngestResourceHost,"") {
           # Only the metadata files exist on stagingResc01 and need to be deleted
           if ( *dropzoneType == "mounted" ){
              msiExecCmd("disable-ingest-zone.sh", "/mnt/stagingResc01/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
           }
           # Disabling the ingest zone needs to be executed on remote ires server
           else if ( *dropzoneType == "direct" ){
              msiExecCmd("disable-ingest-zone.sh", "/mnt/stagingResc01/ingest/direct/" ++ *token, "null", "null", "null", *OUT);
           }
        }
    }
}
