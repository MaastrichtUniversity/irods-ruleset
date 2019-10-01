# Call with
#
# irule -F getProjectCollectionsArray.r "*project='P000000001'" "*inherited='false'"
#
# This is an optimized and combined version of 'detailsProject.r' and 'detailsProjectCollection.r'.
# It is specifically optimized for the pacman portal to render the listing of collections in a project.
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
    IRULE_getProjectCollectionsArray(*project, *inherited, *result);

    writeLine("stdout", *result);
}

IRULE_getProjectCollectionsArray(*project, *inherited, *result) {
    *details = "";

    #####################################################
    ### Get metadata and permissions on PROJECT level ###
    #####################################################
    listProjectContributors(*project, *inherited, *contributors);
    listProjectManagers(*project,*managers);
    listProjectViewers(*project, *inherited, *viewers);

    getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
    getCollectionAVU("/nlmumc/projects/*project","title",*title,"","true");
    getCollectionAVU("/nlmumc/projects/*project","OBI:0000103",*principalInvestigator,"","true");
    getCollectionAVU("/nlmumc/projects/*project","responsibleCostCenter",*respCostCenter,"","true");
    getCollectionAVU("/nlmumc/projects/*project","storageQuotaGb",*storageQuotaGiB,"","true");

    ########################################
    ### Get metadata on COLLECTION level ###
    ########################################
    # JSON object for each collection
    *collection = '{}';
    # JSON array to store all the collections of the input project
    *collectionsArray = '[]';
    *collectionsArraySize = 0;
    # Flag variable to keep the last COLL_NAME inserted into *collectionsArray
    # Warning: expected first default value. Need a more robust check
    *previousCollection = "/nlmumc/projects/*project/C000000001";

    # Key pair Value object to check the expected AVUs from a collection
    *validation."dcat:byteSize" = "";
    *validation."title" = "";
    *validation."creator" =  "";
    *validation."PID" = "";
    *validation."numFiles" = "";

    # Prepare and execute query
    # INFO: The order of elements in *param will influence the alphabetical sorting of the result set.
    # Here, all results from the same COLL_NAME group together (1st level sort), then ascending on META_COLL_ATTR_NAME (2nd level sort), etc.
    *param = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE";
    *cond = "COLL_PARENT_NAME = '/nlmumc/projects/*project'";
    msiMakeGenQuery(*param, *cond, *Query);
    msiExecGenQuery(*Query, *QOut);
    # Gets the continue index value generated by msiExecGenQuery
    # Determine whether there are remaining rows to retrieve from the generated query
    msiGetContInxFromGenQueryOut(*QOut, *cont);
    while (*cont  >= 0){
        # Loop over SQL result and generate JSON array with project info
        foreach (*Row in *QOut){
            *projectCollection = *Row.COLL_NAME;
            *attr = *Row.META_COLL_ATTR_NAME;
            *value = *Row.META_COLL_ATTR_VALUE;

            # We're looping over all AVUs for all projectCollections at once. We need to keep track of the collection that we're processing
            # and compare that to the collection of the previous iteration of the loop.
            # When the current *Row has a different COLL_NAME than the previous iteration, we sum finalize the json
            # for the previous collection and reset everything before continuing the loop.
            if (*previousCollection != *projectCollection){
                # Check for missing attribute and put the default value
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
            # Update KVP *validation with the current pair of AV
            *validation."*attr" = *value;

            # Append each metadata key pair value in *collection
            msiString2KeyValPair("", *kvp);
            msiAddKeyVal(*kvp, *attr , *value);
            msi_json_objops(*collection, *kvp, "add");
        }
        if (*cont  == 0){
            # If the continuation index is 0 the query will be closed
            break;
        }
        msiGetMoreRows(*Query, *QOut, *cont);
    }
    msiCloseGenQuery(*Query, *QOut);

    # Append last *collection iteration in *collectionsArray
    if (*collection != "{}"){
        # Check for missing attribute and put the default value
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

    #######################################
    ### Validate PROJECT level metadata ###
    #######################################
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

    ##################################
    ### Construct final json array ###
    ##################################
    *details = '{"project":"*project", "collections": *collectionsArray, "resource": "*resourceStr", "storageQuotaGiB": "*storageQuotaGiBStr", "respCostCenter": "*respCostCenterStr", "principalInvestigator": "*principalInvestigatorStr", "managers": *managers, "contributors": *contributors, "viewers": *viewers}';
    # Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
    msiString2KeyValPair("", *titleKvp);
    msiAddKeyVal(*titleKvp, "title", *title);
    msi_json_objops(*details, *titleKvp, "add");

    *result = *details;
}

INPUT *project="", *inherited=""
OUTPUT ruleExecOut