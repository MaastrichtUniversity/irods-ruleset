# This rule will calculate the size of a collection distributed over (multiple) resources
# E.g. 100 GiB on replRescUM01, 50 GiB on replRescUMCeph01
# WARNING: This can become very compute expensive!
#
# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/calcCollectionSizeAcrossResc.r "*collection='/nlmumc/projects/P000000001/C000000001'" "*unit='GiB'" "*round='ceiling'"
# 
# Rounding options
# *round='none' returns float with decimals
# *round='ceiling' returns integer rounded up 
# *round='floor' returns integer rounded down
#
# Output:
# This rule outputs the same information both in json and iRODS list format

irule_dummy() {
    IRULE_calcCollectionSizeAcrossResc(*collection, *unit, *round, *result, *resultIdList, *resultSizeList);
    writeLine("stdout", *result);
}

IRULE_calcCollectionSizeAcrossResc(*collection, *unit, *round, *result, *resultIdList, *resultSizeList) {
    # Initialize variables
    *resources; # Key pair Value object to store resource type for each resource. key -> resource ID; value ->  "parent" or "orphan"
    *rescSizeArray = '[]';
    *rescIdList = list();
    *rescSizeList = list();

    # Determine all this collection's resources and their parent/orphan type
    getResourcesInCollection(*collection, *resources);

    # Loop over the resources key-value object
    foreach ( *rescId in *resources ) {
        *sizeBytes = 0;

        # Loop over and sum the size of all distinct files in this collection-resource combination
        if ( *resources.*rescId == "parent" ) { # if the value of *rescId equals parent
            foreach ( *Row in SELECT DATA_ID, DATA_SIZE WHERE COLL_NAME like "*collection%" and RESC_PARENT = *rescId) {
                *sizeBytes = *sizeBytes + double(*Row.DATA_SIZE);
            }
        } else if ( *resources.*rescId == "orphan" ) { # if the value of *rescId equals orphan
            foreach ( *Row in SELECT DATA_ID, DATA_SIZE WHERE COLL_NAME like "*collection%" and RESC_ID = *rescId) {
                *sizeBytes = *sizeBytes + double(*Row.DATA_SIZE);
            }
        } else {
            failmsg(-1, "Error with determining storage resource type");
        }

        # Convert to different unit
        if ( *unit == "B" ) {
            *size = *sizeBytes;
        } else if ( *unit == "KiB" ) {
            *size = *sizeBytes/1024;
        } else if ( *unit == "MiB" ) {
            *size = *sizeBytes/1024/1024;
        } else if ( *unit == "GiB" ) {
            *size = *sizeBytes/1024/1024/1024;
        } else if ( *unit == "TiB" ) {
            *size = *sizeBytes/1024/1024/1024/1024;
        } else {
            failmsg(-1, "Invalid input for 'unit'. Options are: B | KiB | MiB | GiB | TiB");
        }

        # Do the rounding
        if ( *unit == "B" ) {
            *roundedSize = trimr(str(*size), "."); # Because typecasting to int leads to incorrect value , we use trimr to get rid of the decimal places.
        } else {
            if ( *round == "none") {
                *size = *size;
            } else if ( *round == "floor") {
                *size = floor(*size);
            } else if ( *round == "ceiling") {
                *size = ceiling(*size);
            } else {
                failmsg(-1, "Invalid input for 'round'. Options are: none | floor | ceiling");
            }
            *roundedSize = str(*size);
        }

        # Collect the values for this iteration and add it to the json array
        *jsonArr = '{"resourceID": "*rescId", "dataSize": "*roundedSize"}';
        json_arrayops_add(*rescSizeArray, *jsonArr);

        # Add the same values to the list object
        *rescIdList = cons(*rescId, *rescIdList);
        *rescSizeList = cons(*roundedSize, *rescSizeList);
    }

    # Return the full json object as result
    *jsonStr = '';
    msiString2KeyValPair("", *kvp);
    msiAddKeyVal(*kvp, 'sizePerResc', *rescSizeArray);
    msi_json_objops(*jsonStr, *kvp, "set");
    *result = *jsonStr;

    # Also return as lists (for easy usage in other rules)
    *resultIdList = *rescIdList;
    *resultSizeList = *rescSizeList;

}

INPUT *collection="",*unit="",*round=""
OUTPUT ruleExecOut
