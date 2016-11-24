# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within ingest.r rule

ingestNestedDelay1(*srcColl, *project, *title, *mirthMetaDataUrl, *token) {
    *validateRepCounter = "";
    queryAVU(*srcColl,"validateRepCounter",*validateRepCounter);

    if(int(*validateRepCounter) == 10) {
        # It's not going to happen, set the state to error-reaching-validator
        msiAddKeyVal(*metaKV, "state", "error-reaching-validator");
        msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");
        failmsg(0, "Finished trying to reach the external validation channel. I give up...");
    }

    if(int(*validateRepCounter) > 0) {
        # This REPEAT cannot be executed
        failmsg(-1, "Validate rule did not execute. I'm trying again...");

    }else{
        # Validation channel has been reached. Now we can query for validation-outcome.
        *validateState ="";
        queryAVU(*srcColl,"validateState",*validateState);

        if ( *validateState == "incorrect" ) {
            setErrorAVU(*srcColl,"state", "warning-validation-incorrect", "Metadata is incorrect") ;
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
            ingestNestedDelay2(*srcColl, *project, *title, *mirthMetaDataUrl, *token);
        }
    }
}
