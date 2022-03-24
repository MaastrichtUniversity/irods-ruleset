# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within post_ingest.py rule

delayRemoveDropzone(*srcColl, *ingestResourceHost, *token, *dropzoneType) {
     msi_getenv("IRODS_INGEST_REMOVE_DELAY", *irodsIngestRemoveDelay)

     delay("<PLUSET>*irodsIngestRemoveDelay</PLUSET>") {
        *error = errorcode(msiRmColl(*srcColl, "forceFlag=", *OUT));

        if ( *error < 0 ) {
            setErrorAVU(*srcColl,"state", "error-post-ingestion","Error removing Dropzone-collection");
        }

        if ( *dropzoneType == "mounted" ){
            remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
                msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
            }
        }
    }
}
