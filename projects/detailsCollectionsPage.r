# Call with
#
# irule -F detailsCollectionsPage.r "*project='P000000001'" "*inherited='false'"
#
# Optimized version of detailsProject.r to render the project web page
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
    IRULE_detailsCollectionsPage(*project, *inherited, *result);

    writeLine("stdout", *result);
}

IRULE_detailsCollectionsPage(*project, *inherited, *result) {
    *details = "";

    listProjectContributors(*project, *inherited, *contributors);
    listProjectManagers(*project,*managers);
    listProjectViewers(*project, *inherited, *viewers);

    getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
    getCollectionAVU("/nlmumc/projects/*project","title",*title,"","true");
    getCollectionAVU("/nlmumc/projects/*project","OBI:0000103",*principalInvestigator,"","true");
    getCollectionAVU("/nlmumc/projects/*project","responsibleCostCenter",*respCostCenter,"","true");
    getCollectionAVU("/nlmumc/projects/*project","storageQuotaGb",*storageQuotaGiB,"","true");

    # JSON object for each collection
    *collection = '{}';
    # JSON array to store all the collections of the input project
    *collectionsArray = '[]';
    *collectionsArraySize = 0;
    # Flag variable to keep the last COLL_NAME inserted into *collectionsArray
    *previousCollection = "/nlmumc/projects/*project/C000000001";

    # Key pair Value object to check the expected collection AVUs
    *validation."dcat:byteSize" = "";
    *validation."title" = "";
    *validation."creator" =  "";
    *validation."PID" = "";
    *validation."numFiles" = "";

    foreach ( *Row in SELECT COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project'){
        *projectCollection = *Row.COLL_NAME;
        *attr = *Row.META_COLL_ATTR_NAME;
        *value = *Row.META_COLL_ATTR_VALUE;

        # When the current *Row has a different COLL_NAME than the previous iteration
        if ( *previousCollection != *projectCollection){
            # Check for missing attribute and put default value
            foreach(*attribute in *validation) {
                if ( *validation.*attribute == ""){
                    msiString2KeyValPair("", *kvp);
                    msiAddKeyVal(*kvp, *attribute, "N/A");
                    msi_json_objops(*collection, *kvp, "add");

                    msiWriteRodsLog("WARNING: The attribute *attribute of *projectCollection has no value in iCAT. Using default value 'N/A'",0);
                }
            }
            # Add collectionID to *collection
            uuChopPath(*previousCollection, *dir, *collectionId);
            msiString2KeyValPair("", *kvp);
            msiAddKeyVal(*kvp, "collection", *collectionId);
            msi_json_objops(*collection, *kvp, "add");
            # Append *collection in *collectionsArray
            msi_json_arrayops(*collectionsArray, *collection, "add", *collectionsArraySize);

             # Reset *collection and *validation
            *collection = '{}';
            *validation;
            *validation."dcat:byteSize" = "";
            *validation."title" ="";
            *validation."creator" =  "";
            *validation."PID" = "";
            *validation."numFiles" = "";

            # Set *previousCollection to current *Row.COLL_NAME
            *previousCollection = *projectCollection;
        }
        *validation."*attr" = *value;

        # Append each metadata key pair value in *collection
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, *attr , *value);
        msi_json_objops(*collection, *kvp, "add");
    }
    # Append last *collection iteration in *collectionsArray
    if (*collection != "{}"){
        foreach(*attribute in *validation) {
          if ( *validation.*attribute == ""){
            msiString2KeyValPair("", *kvp);
            msiAddKeyVal(*kvp, *attribute, "N/A");
            msi_json_objops(*collection, *kvp, "add");

            msiWriteRodsLog("WARNING: The attribute *attribute of *projectCollection has no value in iCAT. Using default value 'N/A'",0);
          }
        }
        uuChopPath(*previousCollection, *dir, *collectionId);
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, "collection", *collectionId);
        msi_json_objops(*collection, *kvp, "add");
        msi_json_arrayops(*collectionsArray, *collection, "add", *collectionsArraySize);
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

    *details = '{"project":"*project", "collections": *collectionsArray, "resource": "*resourceStr", "storageQuotaGiB": "*storageQuotaGiBStr", "respCostCenter": "*respCostCenterStr", "principalInvestigator": "*principalInvestigatorStr", "managers": *managers, "contributors": *contributors, "viewers": *viewers}';
    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="", *inherited=""
OUTPUT ruleExecOut