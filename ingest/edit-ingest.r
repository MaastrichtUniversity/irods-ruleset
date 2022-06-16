# Call with
#
# irule -F edit-ingest.r "*dropzonePath='/nlmumc/ingest/zones/crazy-frog"'" "*project='P000000001'" "*title='bar'"

editIngest {
    # Check for valid state to edit a drop zone
    getCollectionAVU(*dropzonePath,"state",*state,"","true");
    *ingestable = ""
    is_dropzone_state_ingestable(*state, *ingestable)
    if ( *ingestable != "true" ) {
        failmsg(-1, "Invalid state to edit drop zone.");
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);

    msiSetKeyValuePairsToObj(*metaKV, *dropzonePath, "-C");

}

INPUT *user="",*dropzonePath="",*title="",*project=""
OUTPUT ruleExecOut
