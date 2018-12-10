# Call with
#
# irule -F detailsProjectCollection.r "*project='P000000001'" "*collection='C00000001'" "*inherited='false'"
#
# Role inheritance
# *inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
# *inherited='false' only shows explicit contributors. i.e. A contributor only has WRITE access


irule_dummy() {
    IRULE_detailsProjectCollection(*project, *collection, *inherited, *result);

    writeLine("stdout", *result);
}

IRULE_detailsProjectCollection(*project, *collection, *inherited, *result) {
    *details = "";

    getCollectionAVU("/nlmumc/projects/*project/*collection","title",*title,"no-title-set","false");
    getCollectionAVU("/nlmumc/projects/*project/*collection","creator",*creator,"","true");
    getCollectionAVU("/nlmumc/projects/*project/*collection","numFiles",*numFiles,"","true");
    getCollectionAVU("/nlmumc/projects/*project/*collection","PID",*PID,"no-PID-set","false");
    getCollectionSize("/nlmumc/projects/*project/*collection", "B", "none", *byteSize);

    listProjectManagers(*project, *managers);
    listProjectContributors(*project, *inherited, *contributors);
    listProjectViewers(*project, *inherited, *viewers);
    
    *details = '{"project": "*project", "collection": "*collection", "creator": "*creator", "numFiles": "*numFiles", "PID": "*PID", "byteSize": *byteSize, "managers": *managers, "contributors": *contributors, "viewers": *viewers}';

    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="",*collection="",*inherited=""
OUTPUT ruleExecOut

