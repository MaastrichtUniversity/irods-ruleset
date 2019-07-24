# Call with
#
# irule -F detailsProject.r "*project='P000000001'" "*inherited='false'"
#
# Role inheritance
# *inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
# *inherited='false' only shows explicit contributors. i.e. A contributor only has WRITE access


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
    getCollectionAVU("/nlmumc/projects/*project","OBI:0000103",*principalInvestigator,"","true");
    getCollectionAVU("/nlmumc/projects/*project","responsibleCostCenter",*respCostCenter,"","true");
    # TODO: This attribute is deprecated and should be deleted
    getCollectionAVU("/nlmumc/projects/*project","NCIT:C88193",*pricePerGBPerYear,"","false");
    getCollectionAVU("/nlmumc/projects/*project","storageQuotaGb",*storageQuotaGiB,"","true");
    getProjectCost(*project, *projectCost, *collections)

    # Validate the contents of the retrieved AVUs
    if ( *resource == "" ) {
        *resourceStr = "no-resource-AVU-set";
    } else {
        *resourceStr = *resource;
    }

    if ( *title == "" ) {
        *titleStr = "no-title-AVU-set";
    } else {
        *titleStr = *title;
    }

    if ( *principalInvestigator == "" ) {
        *principalInvestigatorStr = "no-principalInvestigator-AVU-set";
    } else {
        *principalInvestigatorStr = *principalInvestigator;
    }

    if ( *respCostCenter == "" ) {
        *respCostCenterStr = "no-respCostCenter-AVU-set";
    } else {
        *respCostCenterStr = *respCostCenter;
    }

    # TODO: This attribute is deprecated and should be deleted
    if ( *pricePerGBPerYear == "" ) {
        *pricePerGBPerYearStr = "no-pricePerGBPerYear-AVU-set";
    } else {
        *pricePerGBPerYearStr = *pricePerGBPerYear;
    }

    if ( *storageQuotaGiB == "" ) {
        *storageQuotaGiBStr = "storageQuotaGiB-AVU-set";
    } else {
        *storageQuotaGiBStr = *storageQuotaGiB;
    }

    # Calculate the size of this project
    *projSize = double(0);
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
        *projectCollection = *Row.COLL_NAME;
        getCollectionSize(*projectCollection, "GiB", "none", *collSize) # *collSize is the result variable that will be created by this rule
        *projSize = *projSize + double(*collSize);
    }
    *projSize = ceiling(*projSize);

    *details = '{"project":"*project", "projectStorageCost": "*projectCost", "collections": *collections, "resource": "*resourceStr", "dataSizeGiB": "*projSize", "storageQuotaGiB": "*storageQuotaGiBStr", "pricePerGBPerYear": "*pricePerGBPerYearStr", "respCostCenter": "*respCostCenterStr", "principalInvestigator": "*principalInvestigatorStr", "managers": *managers, "contributors": *contributors, "viewers": *viewers}';
    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="", *inherited=""
OUTPUT ruleExecOut

