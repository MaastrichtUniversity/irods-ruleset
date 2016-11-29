# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within ingestNestedDelay1.r rule

ingestNestedDelay2(*srcColl, *project, *title, *mirthMetaDataUrl, *token) {
    *error = errorcode(createProjectCollection(*project, *projectCollection, *title));
    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-ingestion","Error creating projectCollection") ;
    }

    *dstColl = "/nlmumc/projects/*project/*projectCollection";

    msiWriteRodsLog("Ingesting *srcColl to *dstColl", 0);

    # Do not specify target resource here! Policy ensures that data is moved to proper resource and
    # if you DO specify it, the ingest workflow will crash with errors about resource hierarchy.
    *error = errorcode(msiCollRsync(*srcColl, *dstColl, "null", "IRODS_TO_IRODS", *status));
    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-ingestion","Error rsyncing ingest zone") ;
    }

    # Send metadata
    *error = errorcode(sendMetadata(*mirthMetaDataUrl,*project, *projectCollection));

    if ( *error < 0 ) {
        setErrorAVU(*srcColl,"state", "error-post-ingestion","Error sending MetaData for indexing ") ;
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
    *code = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

    delay("<PLUSET>1m</PLUSET>") {
        *resourceHost = '';
        queryAVU("/nlmumc/projects/*project","ingestResource",*ingestResource);

        # Obtain the resource host from the specified ingest resource
        foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
            *ingestResourceHost = *r.RESC_LOC;
        }

        msiWriteRodsLog("Resource host *ingestResourceHost", 0);
        msiRmColl(*srcColl, "forceFlag=", *OUT);
        remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
            msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
        }
    }
}
