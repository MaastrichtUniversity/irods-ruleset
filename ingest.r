# Call with
#
# irule -F ingest.r "*token='creepy-click'"

ingest {
    *srcColl = /nlmumc/ingest/zones/*token;

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        failmsg(-814000, "Unknown ingest zone *token");
    }

    *project = ""; *title = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
        if ( *av.META_COLL_ATTR_NAME == "project" ) {
            *project = *av.META_COLL_ATTR_VALUE;
        }
        if ( *av.META_COLL_ATTR_NAME == "title" ) {
            *title = *av.META_COLL_ATTR_VALUE;
        }
    }

    if ( *project == "" ) {
        failmsg(-1, "project is empty!");
    }

    msiAddKeyVal(*metaKV, "state", "validating");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
  
    msiWriteRodsLog("Starting validation of *srcColl", 0);
    # Validate metadata
    # TODO: This should possibly be done on a delayed queue, as Mirthconnect may timeout   
    validateMetadataFromIngest(*token);
    
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthMetaDataUrl)


    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 20 TIMES</EF>") {
        *validateState ="";
        queryAVU(*srcColl,"validateState",*validateState);

        if ( *validateState == "incorrect" ) {
              setErrorAVU(*srcColl,"state", "incorrect-validation","Metadata is incorrect") ;
         }

        if ( *validateState != "validated" ) {
            failmsg(-1, "Metadata not validated yet");
        }

        msiAddKeyVal(*metaKV, "state", "ingesting");
        msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

        msiWriteRodsLog("Starting ingestion *srcColl", 0);

        # On a new delay queue, as we do not want to repeat this part after failure as above
        # We also do not want any repeats of this, as this would create a new project collection
        delay("<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF>") {

            *error = errorcode(createProjectCollection(*project, *projectCollection));
            if ( *error < 0 ) {
                setErrorAVU(*srcColl,"state", "error-ingestion","Error creating projectCollection") ;
            }

            *dstColl = "/nlmumc/projects/*project/*projectCollection";

            msiWriteRodsLog("Ingesting *srcColl to *dstColl", 0);

            # Do not specify target resource here! Policy ensures that data is moved to proper resource and if you DO specify it, the ingest workflow will crash with errors about resource hierarchy.
            *error = errorcode(msiCollRsync(*srcColl, *dstColl, "null", "IRODS_TO_IRODS", *status));
            if ( *error < 0 ) {
                setErrorAVU(*srcColl,"state", "error-ingestion","Error rsyncing ingest zone") ;
            }

            msiAddKeyVal(*titleKV, "title", *title);
            msiGetObjType(*dstColl, *objType);
            msiSetKeyValuePairsToObj(*titleKV, *dstColl, *objType);
            
            # Send Meta data
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
                    *ingestResourceHost = *r.RESC_LOC
                }

                msiWriteRodsLog("Resource host *ingestResourceHost", 0);
                msiRmColl(*srcColl, "forceFlag=", *OUT);
                remote(*ingestResourceHost,"") { # Disabling the ingest zone needs to be executed on remote ires server
                    msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
                }
            }
        }
    }
}

INPUT *token=""
OUTPUT ruleExecOut
