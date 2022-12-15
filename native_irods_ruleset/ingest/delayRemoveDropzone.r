# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within post_ingest.py rule

delayRemoveDropzone(*srcColl, *ingestResourceHost, *token, *dropzoneType) {
     *irodsIngestRemoveDelay = ""
     get_env("IRODS_INGEST_REMOVE_DELAY", "true", *irodsIngestRemoveDelay)

     delay("<PLUSET>*irodsIngestRemoveDelay</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        *error = errorcode(msiRmColl(*srcColl, "forceFlag=", *OUT));

        if ( *error < 0 ) {
            setErrorAVU(*srcColl,"state", "error-post-ingestion","Error removing Dropzone-collection");
        }

        remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
           if ( *dropzoneType == "mounted" ){
              msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
           }
           else if ( *dropzoneType == "direct" ){
              msiExecCmd("disable-ingest-zone.sh", "/mnt/stagingResc01/ingest/direct/" ++ *token, "null", "null", "null", *OUT);
           }
        }
    }
}
