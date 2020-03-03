# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within ingestNestedDelay1.r rule

ingestNestedDelay2(*srcColl, *project, *title, *mirthMetaDataUrl, *user, *token) {
    msiWriteRodsLog("Starting ingestion *srcColl", 0);
    msiAddKeyVal(*stateKV, "state", "ingesting");
    msiSetKeyValuePairsToObj(*stateKV, *srcColl, "-C");

    *error = errorcode(createProjectCollection(*project, *projectCollection, *title));
    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-ingestion","Error creating projectCollection") ;
    }

    *dstColl = "/nlmumc/projects/*project/*projectCollection";

    msiWriteRodsLog("Ingesting *srcColl to *dstColl", 0);

    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");

    # Obtain the resource host from the specified ingest resource
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
         *ingestResourceHost = *r.RESC_LOC;
    }
    msiWriteRodsLog("DEBUG: Resource host *ingestResourceHost", 0);
       
    # Determine pre-ingest time to calculate average ingest speed
    *time = time();
    *strtime = timestrf(*time, "%s");
    *before = double(*strtime);

    # Ingest the files from local directory on resource server to iRODS collection
    remote(*ingestResourceHost,"") {
        # You can enter any string for the *resc argument in 'msiput_dataobj_or_coll'. Policy will ensure that data will be copied to proper resource.
        # Note: do not enter the value 'null' for *resc. That will cause the microservice to error out.
        *error = errorcode(msiput_dataobj_or_coll("/mnt/ingest/zones/*token", "dummy_resource", "numThreads=10++++forceFlag=", *dstColl, *real_path));
    }  
    msiWriteRodsLog("DEBUG: Done remote", 0);

    if ( *error < 0 ) {
        setErrorAVU(*srcColl, "state", "error-ingestion","Error copying ingest zone") ;
    }

    # Determine post-ingest time to calculate average ingest speed
    *time = time();
    *strtime = timestrf(*time, "%s");
    *after = double(*strtime);  
    *difference = double(*after - *before)+1;

    # Calculate the number of files and total size of the ProjectCollection
    calcCollectionSize(*dstColl, "B", "ceiling", *size);
    calcCollectionFiles(*dstColl, *numFiles);

    # Calculate average ingest speed
    *result = double(*size);
    *avgSpeed = (*result/1024/1024)/*difference;
    *sizeGiB = double(*size)/1024/1024/1024
    msiWriteRodsLog("*srcColl : Ingested *sizeGiB GiB in *numFiles files", 0);
    msiWriteRodsLog("*srcColl : Sync took *difference seconds", 0);
    msiWriteRodsLog("*srcColl : AVG speed was *avgSpeed MiB/s", 0);

    # Set simple AVUs
    msiWriteRodsLog("*srcColl : Setting AVUs to *dstColl", 0);
    msiAddKeyVal(*metaKV, "creator", *user);
    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");

    # Calculate and set the byteSize and numFiles AVU. false/false because collection is already open and needs to stay open
    setCollectionSize(*project, *projectCollection, "false", "false");

    # Send metadata
    # Please note that this step also sets the PID AVU via MirthConnect
    *error = errorcode(sendMetadata(*mirthMetaDataUrl,*project, *projectCollection));

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-post-ingestion","Error sending metadata for indexing");
    }

    # Close collection by making all access read only
    closeProjectCollection(*project, *projectCollection);

    msiWriteRodsLog("Finished ingesting *srcColl to *dstColl", 0);

    msiAddKeyVal(*stateKV, "state", "ingested");
    msiSetKeyValuePairsToObj(*stateKV, *srcColl, "-C");

    # The unmounting of the physical mount point is not done in the delay() where msiRmColl on the token is done.
    # This is because of a bug in the unmount. This is kept in memory for
    # the remaining of the irodsagent session.
    # See also: https://groups.google.com/d/msg/irod-chat/rasDT-AGAVQ/Bb31VJ9SAgAJ
    *error = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-post-ingestion","Error unmounting");
    }

    # Get environment config option for setting the delay for drop zone removal
    msi_getenv("IRODS_INGEST_REMOVE_DELAY", *irodsIngestRemoveDelay);

    delay("<PLUSET>*irodsIngestRemoveDelay</PLUSET>") {
        *error = errorcode(msiRmColl(*srcColl, "forceFlag=", *OUT));

        if ( *error < 0 ) {
            setErrorAVU(*srcColl,"state", "error-post-ingestion","Error removing Dropzone-collection");
        }

        remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
            msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
        }
    }
}
