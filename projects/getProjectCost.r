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
    IRULE_getProjectCost(*project, *result, *collections);

    writeLine("stdout", *result);
}

IRULE_getProjectCost(*project, *result, *collections) {

    *pricePerGBPerYearAttr = "NCIT:C88193";
    *pricePerGBPerYearStr = "";
    *details = "";
    *collections_json = '[]';
    *arraySize = 0;
    *projectCost = 0;
    *result = 0;


    # Calculate the cost of this project
    # Looping over collections
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
        *projectCollection = *Row.COLL_NAME;

        # Get the total size of this collection in GiB (for displaying)
        getCollectionSize(*projectCollection, "GiB", "none", *collSize) # *collSize is the result variable that will be created by this rule

        # Loop on collection's AVU
        *resourceDetails = '[]';
        *detailsArraySize = 0;
        *collectionCost = 0;
        *resourceId = "";

        # Looping over resource-AVUs
        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*projectCollection" ) {
            # Check dcat:byteSize AVU for each resource
            if ( *av.META_COLL_ATTR_NAME like regex "dcat:byteSize_resc_([0-9])+" ) {
                *value = *av.META_COLL_ATTR_VALUE;
                *name = *av.META_COLL_ATTR_NAME;
                *resourceId = triml(*name, "resc_");

                # Convert to GB (for calculation and display of costs)
                *sizeOnResource = double(*value)/1000/1000/1000;

                # Lookup the price for this resource
                *pricePerGBPerYearStr = "";
                foreach (*av in SELECT META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_ID== "*resourceId") {
                    if ( *av.META_RESC_ATTR_NAME == *pricePerGBPerYearAttr) {
                        *pricePerGBPerYearStr = *av.META_RESC_ATTR_VALUE;
                    }
                }
                if ( *pricePerGBPerYearStr == "" ) {
                    failmsg(-1, "Resource ID '*resourceId': no attribute called '*pricePerGBPerYearAttr' found");
                }

                *storageCostOnResc = *sizeOnResource * double(*pricePerGBPerYearStr);
                *collectionCost = *collectionCost + *storageCostOnResc;

                # Add the results for this resource to the Json
                *details = '{"resource": "*resourceId", "dataSizeGBOnResource": "*sizeOnResource", "pricePerGBPerYear": "*pricePerGBPerYearStr", "storageCostOnResource": "*storageCostOnResc"}';
                msi_json_arrayops(*resourceDetails, *details, "add", *detailsArraySize);
            }
        }
        # Error out if no byteSize_resc attribute is present for this collection
        if ( *resourceId == "" ) {
            msiWriteRodsLog("WARNING: *projectCollection: no attribute 'dcat:byteSize_resc_<RescID>' found. Using default value of '*collectionCost'",0);
        }

        # Add the results for this collection to the Json
        *collId = triml("*projectCollection","*project"++"/");
        *coll = '{"collection": "*collId", "dataSizeGiB": "*collSize", "detailsPerResource": *resourceDetails, "collectionStorageCost": "*collectionCost"}';
        *projectCost = *projectCost + *collectionCost;
        msi_json_arrayops(*collections_json, *coll, "add", *arraySize);
    }

    # Output the results for the entire project as Json
    *collections = *collections_json;
    *result = *projectCost;
}

INPUT *project=""
OUTPUT ruleExecOut

