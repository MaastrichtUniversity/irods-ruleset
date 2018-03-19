# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within ingestNestedDelay1.r rule

ingestNestedDelay2(*srcColl, *project, *title, *mirthMetaDataUrl, *user, *token) {
    msiWriteRodsLog("Starting ingestion *srcColl", 0);
    msiAddKeyVal(*metaKV, "state", "ingesting");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

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
        # Do not specify target resource here! Policy ensures that data is moved to proper resource and
        # if you DO specify it, the ingest workflow will crash with errors about resource hierarchy.

        *error = errorcode(msiput_dataobj_or_coll("/mnt/ingest/zones/*token", "null", "numThreads=10++++forceFlag=", *dstColl, *real_path));
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

    # Get number of files and total size
    *size = "0";
    *count = 0;
    foreach ( *Row in select sum(DATA_SIZE), count(COLL_NAME) where COLL_NAME like "*dstColl%" AND DATA_REPL_NUM ="0" ) {
       *size = *Row.DATA_SIZE;
       *count = *Row.COLL_NAME; 
    }

    # Calculate average ingest speed
    *result = double(*size);
    *avgSpeed = *result/(*difference*1024*1024);
    msiWriteRodsLog("Sync took  *difference seconds", 0);
    msiWriteRodsLog("AVG speed was *avgSpeed MB/s for *count files ", 0);

    # Add creator AVU (i.e. current user) to project collection
    msiAddKeyVal(*metaKV, "creator", *user);
    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");

    # Send metadata
    *error = errorcode(sendMetadata(*mirthMetaDataUrl,*project, *projectCollection));

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-post-ingestion","Error sending metadata for indexing");
    }

    # Close collection by making all access read only
    closeProjectCollection(*project, *projectCollection);

    msiWriteRodsLog("Finished ingesting *srcColl to *dstColl", 0);

    msiAddKeyVal(*metaKV, "state", "ingested");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

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
