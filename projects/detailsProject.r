# Call with
#
# irule -F detailsProject.r "*project='P000000001'" "*inherited='false'"

irule_dummy() {
    IRULE_detailsProject(*project, *inherited, *result);

    writeLine("stdout", *result);
}

IRULE_detailsProject(*project, *inherited, *result) {
    *details = "";

    listProjectContributors(*project, *inherited, *contributors);
    listProjectManagers(*project,*managers);
    listProjectViewers(*project, *inherited, *viewers);

    getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
    getCollectionAVU("/nlmumc/projects/*project","title",*title,"","true");
    
    *details = '{"project":"*project", "resource": "*resource", "viewers": *viewers,"contributors": *contributors, "managers": *managers}';

    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="", *inherited=""
OUTPUT ruleExecOut

