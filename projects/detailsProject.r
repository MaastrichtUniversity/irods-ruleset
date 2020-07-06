# Call with
#
# irule -F detailsProject.r "*project='P000000001'" "*inherited='false'"
#
# Role inheritance
# *inherited='true' cumulates authorizations to designate the role. i.e. A contributor has OWN or WRITE access
# *inherited='false' only shows explicit contributors. i.e. A contributor only has WRITE access
#
# Please note the different usage of size units:
# - bytes are used for the purpose of storing values in iCAT
# - GB is used for the purpose of calculating and displaying costs
# - GiB is used for the purpose of diplaying the size to end-user


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
    getCollectionAVU("/nlmumc/projects/*project","storageQuotaGb",*storageQuotaGiB,"","true");
    getCollectionAVU("/nlmumc/projects/*project","dataSteward",*dataSteward,"","true");
    # Get the display Name for the dataSteward
    # TODO: Fix the strange iRODS bug where *title cannot be added by msi_json_objops when you add both the *dataSteward and *dataStewardDisplayName to the json string at line 92
    # Therefore the line below is commented out for now
    # getDisplayNameForAccount(*dataSteward,*dataStewardDisplayName)


    *projectCost  = double(0);
    *collections = "{}";
    *projSize = double(0);
    if ($userNameClient == *principalInvestigator || $userNameClient == "rods"  ){
        getProjectCost(*project, *projectCost, *collections, *projSize);
    }
    else{
        # Calculate the total size of this project in GiB (for displaying)
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
            *projectCollection = *Row.COLL_NAME;
            getCollectionSize(*projectCollection, "GiB", "none", *collSize) # *collSize is the result variable that will be created by this rule
            *projSize = *projSize + double(*collSize);
        }
    }

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

    if ( *storageQuotaGiB == "" ) {
        *storageQuotaGiBStr = "storageQuotaGiB-AVU-set";
    } else {
        *storageQuotaGiBStr = *storageQuotaGiB;
    }
    
     if ( *dataSteward == "" ) {
        *dataStewardStr = "no-dataSteward-AVU-set";
    } else {
        *dataStewardStr = *dataSteward;
    }

    *details = '{"project":"*project", "projectStorageCost": "*projectCost", "collections": *collections, "resource": "*resourceStr", "dataSizeGiB": "*projSize", "storageQuotaGiB": "*storageQuotaGiBStr", "respCostCenter": "*respCostCenterStr", "dataSteward": "*dataStewardStr", "principalInvestigator": "*principalInvestigatorStr", "managers": *managers, "contributors": *contributors, "viewers": *viewers}';
    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="", *inherited=""
OUTPUT ruleExecOut

