# Call with
#
# irule -F getProjectCost.r "*project='P000000001'"
#
# Output variables:
# *result: whole project storage cost
# *collections: nested json array for each collection cost
# stdout -> *result

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
    foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects/*project' ) {
        *projectCollection = *Row.COLL_NAME;

        getCollectionSize(*projectCollection, "GiB", "none", *collSize) # *collSize is the result variable that will be created by this rule

        # Loop on collection's AVU
        *resourceDetails = '[]';
        *detailsArraySize = 0;
        *collectionCost = 0;

        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*projectCollection") {
            # Check dcat:byteSize AVU for each resource
            if ( *av.META_COLL_ATTR_NAME like regex "dcat:byteSize_(.+)") {
                *value = *av.META_COLL_ATTR_VALUE;
                *name = *av.META_COLL_ATTR_NAME;

                # GiB
                *sizeOnResource = double(*value)/1024/1024/1024;
                *resourceName = triml(*name, "_");

                *pricePerGBPerYearStr = "";
                # Update pricePerGBPerYearStr with resource's price if no specialPrice is present

                foreach (*av in SELECT META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME == "*resourceName") {
                    if ( *av.META_RESC_ATTR_NAME == *pricePerGBPerYearAttr) {
                        *pricePerGBPerYearStr = *av.META_RESC_ATTR_VALUE;
                    }
                }

                *storageCostOnResc = *sizeOnResource * double(*pricePerGBPerYearStr);
                *collectionCost = *collectionCost + *storageCostOnResc;

                *details = '{"resource": "*resourceName", "dataSizeGiB": "*sizeOnResource", "pricePerGBPerYear": "*pricePerGBPerYearStr", "storageCostOnResource": "*storageCostOnResc"}';
                msi_json_arrayops(*resourceDetails, *details, "add", *detailsArraySize);
            }
        }

        *collId = triml("*projectCollection","*project"++"/");
        *coll = '{"collection": "*collId", "dataSizeGiB": "*collSize", "detailsPerResource": *resourceDetails, "collectionStorageCost": "*collectionCost"}';
        *projectCost = *projectCost + *collectionCost;
        msi_json_arrayops(*collections_json, *coll, "add", *arraySize);
    }

    *collections = *collections_json;
    *result = *projectCost;
}

INPUT *project=""
OUTPUT ruleExecOut

