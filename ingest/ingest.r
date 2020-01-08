# Call with
#
# irule -F ingest.r "*user='username@domain.com'" "*token='creepy-click'"

ingest {
    *srcColl = "/nlmumc/ingest/zones/*token";

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        # CAT_UNKNOWN_COLLECTION
        failmsg(-814000, "Unknown ingest zone *token");
    }

    *state = ""; *project = ""; *title = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == *srcColl) {
        if ( *av.META_COLL_ATTR_NAME == "project" ) {
            *project = *av.META_COLL_ATTR_VALUE;
        }
        if ( *av.META_COLL_ATTR_NAME == "title" ) {
            *title = *av.META_COLL_ATTR_VALUE;
        }
        if ( *av.META_COLL_ATTR_NAME == "state" ) {
            *state = *av.META_COLL_ATTR_VALUE;
        }
    }

    # Check for project's ingest resource status to start ingestion
    getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
    *rescStatus = ""
    foreach (*r in select RESC_STATUS where RESC_NAME = *resource ) {
        *rescStatus = *r.RESC_STATUS;
    }

    # Only down is a real status. Anything but "down" means up
    if ( *rescStatus == "down" ) {
        # -831000 CAT_INVALID_RESOURCE
        failmsg(-831000, "Ingest disabled for this resource.");
    }

    # Check for valid state to start ingestion
    if ( *state != "open" && *state != "warning-validation-incorrect" ) {
        failmsg(-1, "Invalid state to start ingestion.");
    }

    if ( *project == "" ) {
        failmsg(-1, "Project is empty.");
    }

    msiWriteRodsLog("Setting status *srcColl to in queue", 0);
    msiAddKeyVal(*stateKV, "state", "in-queue-for-validation");
    msiSetKeyValuePairsToObj(*stateKV, *srcColl, "-C");

    # Remove validateState. Required due to parallel execution of irods queue
    getCollectionAVU(*srcColl,"validateState",*validateState,"","false");
    if ( *validateState != "" ) {
        msiAddKeyVal(*validateStateKV, "validateState", *validateState );
        msiRemoveKeyValuePairsFromObj(*validateStateKV, *srcColl, "-C");
    }
    
    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 10 TIMES</EF>") {
        # Validate metadata
        *mirthValidationURL = "";
        msi_getenv("MIRTH_VALIDATION_CHANNEL", *mirthValidationURL);
        validateMetadataFromIngest(*token,*mirthValidationURL);
    }

    # Continue ingest and create PID in Mirth
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthMetaDataUrl);

    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 20 TIMES</EF>") {
        ingestNestedDelay1(*srcColl, *project, *title, *mirthMetaDataUrl, *user, *token);
    }
}

INPUT *user="",*token=""
OUTPUT ruleExecOut
