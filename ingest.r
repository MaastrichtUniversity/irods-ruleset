# Call with
#
# irule -F ingest.r "*token='creepy-click'" "*resourceServer='ires'"

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

        *validateState = "";
        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
            if ( *av.META_COLL_ATTR_NAME == "validateState" ) {
                *validateState = *av.META_COLL_ATTR_VALUE;
            }
        }

        if ( *validateState == "incorrect" ) {
            msiAddKeyVal(*metaKV, "state", "incorrect-validation");
            msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
            failmsg(0, "Metadata is incorrect");
        }

        if ( *validateState != "validated" ) {
            failmsg(-1, "Metadata not validated yet");
        }

        msiAddKeyVal(*metaKV, "state", "ingesting");
        msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

        msiWriteRodsLog("Starting ingestion *srcColl", 0);

        # On a new delay queue, as we do not want to repeat this part after failure as above
        delay("<PLUSET>1s</PLUSET>") {

            *error = errorcode(createProjectCollection(*project, *projectCollection));

            if ( *error < 0 ) {
                # TODO: This could be moved to more generic error function
                msiAddKeyVal(*metaKV, "state", "error-ingestion");
                msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
                failmsg(0, "Error creating projectCollection for *srcColl");
            }

            *dstColl = "/nlmumc/projects/*project/*projectCollection";

            msiWriteRodsLog("Ingesting *srcColl to *dstColl", 0);

            # TODO: Handle errors
            # Do not specify target resource here! Policy ensures that data is moved to proper resource and if you DO specify it, the ingest workflow will crash with errors about resource hierarchy.
            msiCollRsync(*srcColl, *dstColl, "null", "IRODS_TO_IRODS", *status);

            msiAddKeyVal(*titleKV, "title", *title);
            msiGetObjType(*dstColl, *objType);
            msiSetKeyValuePairsToObj(*titleKV, *dstColl, *objType);
            
            # Send Meta data
            *error = errorcode(sendMetadata(*mirthMetaDataUrl,*project, *projectCollection));
            
            if ( *error < 0 ) {
                # TODO: This could be moved to more generic error function
                msiAddKeyVal(*metaKV, "state", "error-post-ingestion");
                msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
                failmsg(0, "Error sending MetaData for indexing for *srcColl");
            }            
            
            # Close collection by making all access read only
            closeProjectCollection(*project, *projectCollection);

            msiWriteRodsLog("Finished ingesting *srcColl to *dstColl", 0);

            msiAddKeyVal(*metaKV, "state", "ingested");
            msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

            delay("<PLUSET>1m</PLUSET>") {
                # TODO: Handle errors
                *code = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

                msiRmColl(*srcColl, "forceFlag=", *OUT);
                remote(*resourceServer,"") { # Disabling the ingest zone needs to be executed on remote ires server
                    msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
                }
            }
        }
    }
}

INPUT *token="",*resourceServer=""
OUTPUT ruleExecOut
