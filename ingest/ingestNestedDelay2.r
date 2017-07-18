# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within ingestNestedDelay1.r rule

ingestNestedDelay2(*srcColl, *project, *title, *mirthMetaDataUrl, *user, *token) {
    *error = errorcode(createProjectCollection(*project, *projectCollection, *title));
    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-ingestion","Error creating projectCollection") ;
    }

    *dstColl = "/nlmumc/projects/*project/*projectCollection";

    msiWriteRodsLog("Ingesting *srcColl to *dstColl", 0);

    # Do not specify target resource here! Policy ensures that data is moved to proper resource and
    # if you DO specify it, the ingest workflow will crash with errors about resource hierarchy.
    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");

    # Obtain the resource host from the specified ingest resource
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
         *ingestResourceHost = *r.RESC_LOC;
    }
    msiWriteRodsLog("Resource host *ingestResourceHost", 0);
       
    msiSplitPath(*srcColl,*Coll,*File);

    #Save time before ingest to calculate average ingest speed
    *time = time();
    *strtime = timestrf(*time, "%s");
    *before = double(*strtime);

    #Ingest the files from local directory on resource server to irods collection

    remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
            *error = errorcode(msiput_dataobj_or_coll("/mnt/ingest/zones/*File", "null", "numThreads=10++++forceFlag=", *dstColl,*real_path));
    }  
    msiWriteRodsLog("Done remote", 0);    

    #Save time after ingest to calculate average ingest speed
    *time = time();
    *strtime = timestrf(*time, "%s");
    *after = double(*strtime);  
    *difference = double(*after - *before)+1;
     *size = "0";
    *count = 0;

    #Get number of files and total size
    foreach ( *Row in select sum(DATA_SIZE), count(COLL_NAME) where COLL_NAME like "*dstColl%" AND DATA_REPL_NUM ="0" ) {
       *size = *Row.DATA_SIZE;
       *count = *Row.COLL_NAME; 
    }

    #Calculate avergae ingest speed
    *result = double(*size);
    *avgSpeed = *result/(*difference*1024*1024);
    msiWriteRodsLog("Sync took  *difference seconds", 0);
    msiWriteRodsLog("AVG speed was *avgSpeed Mb/s for *count files ", 0);

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-ingestion","Error rsyncing ingest zone") ;
    }

    # Add creator AVU (i.e. current user) to project collection
    msiAddKeyVal(*metaKV, "creator", *user);
    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");

    # Send metadata
    *error = errorcode(sendMetadata(*mirthMetaDataUrl,*project, *projectCollection));

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-post-ingestion","Error sending MetaData for indexing");
    }

    # Close collection by making all access read only
    closeProjectCollection(*project, *projectCollection);

    msiWriteRodsLog("Finished ingesting *srcColl to *dstColl", 0);

    msiAddKeyVal(*metaKV, "state", "ingested");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    # TODO: Handle errors
    # The unmounting of the physical mount point is not done in the delay() where msiRmColl on the token is done.
    # This is because of a bug in the unmount. This is kept in memory for
    # the remaining of the irodsagent session.
    # See also: https://groups.google.com/d/msg/irod-chat/rasDT-AGAVQ/Bb31VJ9SAgAJ
    *error = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-post-ingestion","Error unmounting");
    }

    delay("<PLUSET>1m</PLUSET>") {
        getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");

        # Obtain the resource host from the specified ingest resource
        foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
            *ingestResourceHost = *r.RESC_LOC;
        }

        msiWriteRodsLog("Resource host *ingestResourceHost", 0);
        *error = errorcode(msiRmColl(*srcColl, "forceFlag=", *OUT));

        if ( *error < 0 ) {
            setErrorAVU(*srcColl,"state", "error-post-ingestion","Error removing Dropzone-collection");
        }

        remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
            msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
        }
    }
}
