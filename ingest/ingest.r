# Call with
#
# irule -F ingest.r "*user='username@domain.com'" "*token='creepy-click'"

ingest {
    *srcColl = "/nlmumc/ingest/zones/*token";

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        failmsg(-814000, "Unknown ingest zone *token");
    }

    *state = ""; *project = "";
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

    # Check for valid state to start ingestion
    if ( *state != "open" && *state != "warning-validation-incorrect" ) {
        failmsg(-1, "Invalid state to start ingestion.");
    }

    if ( *project == "" ) {
        failmsg(-1, "Project is empty.");
    }

    msiWriteRodsLog("Setting status *srcColl to in queue", 0);
    msiAddKeyVal(*metaKV, "state", "in-queue-for-validation");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 10 TIMES</EF>") {
        # Validate metadata
        msi_getenv("MIRTH_VALIDATION_CHANNEL", *mirthValidationURL);
        validateMetadataFromIngest(*token,*mirthValidationURL);
    }

    # Continue ingest and send to Solr
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthMetaDataUrl);

    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 20 TIMES</EF>") {
        ingestNestedDelay1(*srcColl, *project, *title, *mirthMetaDataUrl, *user, *token);
    }
}

INPUT *user="",*token=""
OUTPUT ruleExecOut
