# Call with
#
# irule -F edit-ingest.r "*token='bla-token'" "*project='P000000001'" "*title='bar'"

editIngest {
    *tokenColl = "/nlmumc/ingest/zones/*token";

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);

    msiSetKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

}

INPUT *user="",*token="",*title="",*project="",
OUTPUT ruleExecOut
