# This rule will calculate the size of a collection distributed over (multiple) coordinating resources
# E.g. 100 GiB on replRescUM01, 50 GiB on replRescUMCeph01
# WARNING: This can become very compute expensive!
#
# Call with
#
# irule -F calcCollectionSizeAcrossCoordResources.r "*collection='/nlmumc/projects/P000000001/C000000001'" "*unit='GiB'" "*round='ceiling'"
# 
# Rounding options
# *round='none' returns float with decimals
# *round='ceiling' returns integer rounded up 
# *round='floor' returns integer rounded down
#
# Output:
# This rule outputs the same information both in json and iRODS list format

irule_dummy() {
    IRULE_calcCollectionSizeAcrossCoordResources(*collection, *unit, *round, *result, *resultIdList, *resultSizeList);
    writeLine("stdout", *result);
}

IRULE_calcCollectionSizeAcrossCoordResources(*collection, *unit, *round, *result, *resultIdList, *resultSizeList) {
    *resources = list();

    # Determine all resources used in this collection
    foreach ( *Row in SELECT RESC_PARENT WHERE COLL_NAME like "*collection%") {
        *resources = cons(*Row.RESC_PARENT, *resources);
    }

    *rescSizeArray = '[]';
    *rescIdList = list();
    *rescSizeList = list();

    # Loop over resources list
    foreach ( *resc in *resources ) {
        *sizeBytes = 0;

        # Loop over and sum the size of all distinct files in this collection-resource combination
        foreach ( *Row in SELECT DATA_ID, DATA_SIZE WHERE COLL_NAME like "*collection%" and RESC_PARENT = *resc) {
            *sizeBytes = *sizeBytes + double(*Row.DATA_SIZE);
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
        *jsonArr = '{"resourceID": "*resc", "dataSize": "*roundedSize"}';
        msi_json_arrayops(*rescSizeArray, *jsonArr, "add", 0);

        # Add the same values to the list object
        *rescIdList = cons(*resc, *rescIdList);
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