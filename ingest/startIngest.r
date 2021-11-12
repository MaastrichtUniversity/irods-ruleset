# Call with
#
# irule -F startIngest.r "*user='dlinssen'" "*token='creepy-click'"

startIngest {
    *srcColl = "/nlmumc/ingest/zones/*token";

    *hasDropZonepermission = "";
    checkDropZoneACL(*user, *hasDropZonepermission);
    if (*hasDropZonepermission == "false") {
        # -818000 CAT_NO_ACCESS_PERMISSION
        failmsg(-818000, "User '*user' has insufficient DropZone permissions on /nlmumc/ingest/zones");
    }

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
    msiWriteRodsLog("Starting validation of *srcColl", 0)
    *validationResult = ""
    validate_metadata(*srcColl, *validationResult)
    if (*validationResult == "true") {
        msiWriteRodsLog("Validation result is OK, starting ingest of *srcColl", 0)
        # On a new delay queue, as we do not want to repeat this part after failure as above
        # We also do not want any repeats of this, as this would create a new project collection
        delay("<PLUSET>1s</PLUSET><EF>30s REPEAT 0 TIMES</EF>") {
            performIngest(*srcColl, *project, *title, *user, *token);
        }
    }
    else{
        setErrorAVU(*srcColl, "state", "warning-validation-incorrect", "Metadata is incorrect")
    }
}

INPUT *user="",*token=""
OUTPUT ruleExecOut
