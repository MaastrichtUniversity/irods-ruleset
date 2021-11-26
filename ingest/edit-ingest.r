# Call with
#
# irule -F edit-ingest.r "*token='bla-token'" "*project='P000000001'" "*title='bar'" "*schema_name='DataHub_general_schema'" "*schema_version='0.0.1'"

editIngest {
    *tokenColl = "/nlmumc/ingest/zones/*token";

    # Check for valid state to edit a drop zone
    getCollectionAVU(*tokenColl,"state",*state,"","true");
    if ( *state != "open" && *state != "warning-validation-incorrect" ) {
        failmsg(-1, "Invalid state to edit drop zone.");
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "templateSchemaName", *schema_name);
    msiAddKeyVal(*metaKV, "templateSchemaVersion", *schema_version);

    msiSetKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

}

INPUT *user="",*token="",*title="",*project="",*schema_name="",*schema_version=""
OUTPUT ruleExecOut
