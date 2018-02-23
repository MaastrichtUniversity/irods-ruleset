# Call with
#
# irule -F detailsProjectCollection.r "*project='P000000001'" "*collection='C00000001'"

irule_dummy() {
    IRULE_detailsProjectCollection(*project, *collection, *result);

    writeLine("stdout", *result);
}

IRULE_detailsProjectCollection(*project, *collection, *result) {
    *details = "";

    getCollectionAVU("/nlmumc/projects/*project","title",*title,"","true");
    
    *details = '{}';

    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="",*collection=""
OUTPUT ruleExecOut

