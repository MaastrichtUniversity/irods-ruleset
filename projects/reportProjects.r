# This rule returns a JSON string with information about all projects. Outcome can be used for reporting purposes.
#
# Call with (execute as rodsadmin user with full permission to /nlmumc/projects)
#
# irule -F reportProjects.r

irule_dummy() {
    IRULE_reportProjects(*result);

    writeLine("stdout", *result);
}

IRULE_reportProjects(*result) {
    *jsonStr = '[]';

    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = "/nlmumc/projects" ) {
        # Declare variables
        *outcome = "";
        *size = 0;
        *title = "";
        *resource = "";
        *principalInvestigator = "";
        *respCostCenter = "";
        *pricePerGBPerYear = "";
        *storageQuotaGiB = "";
        *managers = "";
        *viewers = "";
        
        # Retrieve the project from the directory name
        uuChopPath(*Row.COLL_NAME, *dir, *project);

        # Retrieve AVUs based on project
        getCollectionAVU("/nlmumc/projects/*project","title",*title,"","true");
        getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
        getCollectionAVU("/nlmumc/projects/*project","OBI:0000103",*principalInvestigator,"","true");
        getCollectionAVU("/nlmumc/projects/*project","responsibleCostCenter",*respCostCenter,"","true");
        getCollectionAVU("/nlmumc/projects/*project","NCIT:C88193",*pricePerGBPerYear,"","true");
        getCollectionAVU("/nlmumc/projects/*project","storageQuotaGb",*storageQuotaGiB,"","true");

        # Retrieve the project manager(s) and viewers
        listProjectManagers(*project,*managers);
        listProjectViewers(*project,"false",*viewers);

        # Calculate the size of this project
        *projSize = double(0);
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
            *projectCollection = *Row.COLL_NAME;
            getCollectionSize(*projectCollection, "GiB", "none", *collSize) # *collSize is the result variable that will be created by this rule
            *projSize = *projSize + double(*collSize);
        }
        *projSize = ceiling(*projSize);

        # Validate the contents of variables and construct json object
        if ( *title == "" ) {
            *titleStr = "no-title-AVU-set";
        } else {
            *titleStr = *title;
        }

        if ( *resource == "" ) {
            *resourceStr = "no-resource-AVU-set";
        } else {
            *resourceStr = *resource;
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

        # Outcome contains the results from this iteration
        *outcome = '{"project":"*project", "resource": "*resourceStr", "dataSizeGiB": "*projSize", "storageQuotaGiB": "*storageQuotaGiBStr", "pricePerGBPerYear": "*pricePerGBPerYearStr", "respCostCenter": "*respCostCenterStr", "principalInvestigator": "*principalInvestigatorStr", "managers": *managers, "viewers": *viewers}';

        # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
        msiString2KeyValPair("", *titleKvp);
        msiAddKeyVal(*titleKvp, "title", *titleStr);
        msi_json_objops(*outcome, *titleKvp, "add");

        # Append the final outcome to the jsonString
        msi_json_arrayops(*jsonStr, *outcome, "add", *size);
    }

    # jsonStr now contains information about all projects. Return this in the result variable
    *result = *jsonStr;
}

INPUT *result=''
OUTPUT ruleExecOut
