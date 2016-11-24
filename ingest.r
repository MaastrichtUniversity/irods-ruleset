# Call with
#
# irule -F ingest.r "*token='creepy-click'"

ingest {
    *srcColl = "/nlmumc/ingest/zones/*token";

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        failmsg(-814000, "Unknown ingest zone *token");
    }

    # Check for valid state to start ingestion
    *state = "";
    queryAVU(*srcColl,"state",*state);
    if ( *state != "" && *state != "warning-validation-incorrect" ) {
        failmsg(-1, "Invalid state to start ingestion.");
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
        failmsg(-1, "Project is empty.");
    }

    msiAddKeyVal(*metaKV, "state", "validating");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
  
    msiWriteRodsLog("Starting validation of *srcColl", 0);

    # Validate metadata
    msi_getenv("MIRTH_VALIDATION_CHANNEL", *mirthValidationURL);

    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 10 TIMES</EF>") {
        validateMetadataFromIngest(*token,*mirthValidationURL);
    }

    # Continue ingest and send to Solr
    msi_getenv("MIRTH_METADATA_CHANNEL", *mirthMetaDataUrl);

    delay("<PLUSET>1s</PLUSET><EF>30s REPEAT UNTIL SUCCESS OR 20 TIMES</EF>") {
        ingestNestedDelay1(*srcColl, *project, *title, *mirthMetaDataUrl, *token);
    }
}

INPUT *token=""
OUTPUT ruleExecOut
