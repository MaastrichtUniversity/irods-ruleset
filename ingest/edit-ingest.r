# Call with
#
# irule -F edit-ingest.r "*token='bla-token'" "*project='P000000001'" "*title='bar'"

editIngest {
    *tokenColl = "/nlmumc/ingest/zones/*token";

    # Check for valid state to edit a drop zone
    getCollectionAVU(*tokenColl,"state",*state,"","true");
    if ( *state != "open" && *state != "warning-validation-incorrect" ) {
        failmsg(-1, "Invalid state to edit drop zone.");
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);

    msiSetKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

}

INPUT *user="",*token="",*title="",*project=""
OUTPUT ruleExecOut
