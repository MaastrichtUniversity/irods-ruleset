# Call with
#
# irule -F getProjectCost.r "*project='P000000001'"
#
# Output variables:
# *result: whole project storage cost
# *collections: nested json array for each collection cost
# stdout -> *result
#
# Please note the different usage of size units:
# - bytes are used for the purpose of storing values in iCAT
# - GB is used for the purpose of calculating and displaying costs
# - GiB is used for the purpose of diplaying the size to end-user

irule_dummy() {
    IRULE_getProjectCost(*project, *result, *collections, *projectSize);

    writeLine("stdout", *result);
}

IRULE_getProjectCost(*project, *result, *collections, *projectSize) {

    *pricePerGBPerYearAttr = "NCIT:C88193";
    *collectionsArray = "[]";
    *collectionsArraySize = 0;
    *projectCost = 0;
    *projectSize = 0;
    *result = 0;

    # Key pair Value object to store *pricePerGBPerYear for each resource:
    # key -> resource ID
    # value ->  *pricePerGBPerYear
    *resources;
    *resources.init = "0";

    *previousCollection = "/nlmumc/projects/*project/C000000001";
    *resourceDetails = '[]';
    *detailsArraySize = 0;
    *collectionCost = 0;

    # Calculate the cost of this project
    # Looping over collections
    foreach ( *Row in SELECT COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' and  META_COLL_ATTR_NAME like "dcat:byteSize_%") {
        *projectCollection = *Row.COLL_NAME;
        *resourceId = triml(*Row.META_COLL_ATTR_NAME, "resc_");

         # When the current *Row has a different COLL_NAME than the previous iteration
        if (*previousCollection != *projectCollection){
            # Get the total size of this collection in GiB (for displaying)
            getCollectionSize(*previousCollection, "GiB", "none", *collSize);
            *projectSize = *projectSize + double(*collSize);

            uuChopPath(*previousCollection, *dir, *collectionId);
            *collection = '{"collection": "*collectionId", "dataSizeGiB": "*collSize", "detailsPerResource": *resourceDetails, "collectionStorageCost": "*collectionCost"}';

            # Add the results of the previous collection to the Json
            msi_json_arrayops(*collectionsArray, *collection, "add", *collectionsArraySize);
            *projectCost = *projectCost + *collectionCost;

            # Reset
            *previousCollection = *projectCollection;
            *resourceDetails = '[]';
            *collectionCost = 0;
        }

        # Lookup the price for this resource
        *pricePerGBPerYearStr = "";
        *queryForPriceOnResource = true;
        foreach(*ID in *resources) {
            if ( *ID == *resourceId){
                *pricePerGBPerYearStr = *resources.*ID;
                *queryForPriceOnResource = false;
                break;
            }
        }
        # Only query if *pricePerGBPerYearStr was not found in *resources
        if (*queryForPriceOnResource){
            foreach (*av in SELECT META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_ID = "*resourceId" and META_RESC_ATTR_NAME = "*pricePerGBPerYearAttr") {
                *resources."*resourceId" = *av.META_RESC_ATTR_VALUE;
                *pricePerGBPerYearStr = *av.META_RESC_ATTR_VALUE;
            }
        }

        if (*pricePerGBPerYearStr == "") {
            failmsg(-1, "Resource ID '*resourceId': no attribute called '*pricePerGBPerYearAttr' found");
        }

        # Convert to GB (for calculation and display of costs)
        *sizeOnResource = double(*Row.META_COLL_ATTR_VALUE)/1000/1000/1000;

        # Calculate cost
        *storageCostOnResc = *sizeOnResource * double(*pricePerGBPerYearStr);
        *collectionCost = *collectionCost + *storageCostOnResc;

        # Add the results for this resource to the Json
        *details = '{"resource": "*resourceId", "dataSizeGBOnResource": "*sizeOnResource", "pricePerGBPerYear": "*pricePerGBPerYearStr", "storageCostOnResource": "*storageCostOnResc"}';
        msi_json_arrayops(*resourceDetails, *details, "add", *detailsArraySize);

        # Error out if no byteSize_resc attribute is present for this collection
        if ( *resourceId == "" ) {
            msiWriteRodsLog("WARNING: *projectCollection: no attribute 'dcat:byteSize_resc_<RescID>' found. Using default value of '*collectionCost'", 0);
        }
    }
    # Append last *collection iteration in *collectionsArray
    if (*resourceDetails != "[]"){
        getCollectionSize(*projectCollection, "GiB", "none", *collSize);
        *projectSize = *projectSize + double(*collSize);

        uuChopPath(*previousCollection, *dir, *collectionId);
        *collection = '{"collection": "*collectionId", "dataSizeGiB": "*collSize", "detailsPerResource": *resourceDetails, "collectionStorageCost": "*collectionCost"}';

        *projectCost = *projectCost + *collectionCost;
        msi_json_arrayops(*collectionsArray, *collection, "add", *collectionsArraySize);
    }
    # Output the results for the entire project as Json
    *collections = *collectionsArray;
    *result = *projectCost;
}

INPUT *project=""
OUTPUT ruleExecOut

