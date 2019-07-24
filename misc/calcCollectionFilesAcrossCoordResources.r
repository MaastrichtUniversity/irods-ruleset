# This rule will calculate the number of files distributed over (multiple) coordinating resources
# E.g. 100 files on replRescUM01, 50 files on replRescUMCeph01
# Call with
#
# irule -F calcCollectionFilesAcrossCoordResources.r "*collection='/nlmumc/projects/P000000001/C000000001'"
#
# Output:
# This rule outputs the same information both in json and iRODS list format

irule_dummy() {
    IRULE_calcCollectionFilesAcrossCoordResources(*collection, *result, *resultIdList, *resultNumFilesList);
    writeLine("stdout", *result);
}

IRULE_calcCollectionFilesAcrossCoordResources(*collection, *result, *resultIdList, *resultNumFilesList) {
    *resources = list();

    # Determine all resources used in this collection
    foreach ( *Row in SELECT RESC_PARENT WHERE COLL_NAME like "*collection%") {
        *resources = cons(*Row.RESC_PARENT, *resources);
    }

    *rescNumFilesArray = '[]';
    *rescIdList = list();
    *rescNumFilesList = list();

    # Loop over resources list
    foreach ( *resc in *resources ) {
        *count = 0;

        # Loop over all distinct files in in this collection-resource combination
        foreach ( *Row in SELECT DATA_ID WHERE COLL_NAME like "*collection%"  and RESC_PARENT = *resc) {
            # not doing anything with the SQL result, just counting the number of iterations in the loop
            *count = *count + 1;
        }

        # Collect the values for this iteration and add it to the json array
        *jsonArr = '{"resourceID": "*resc", "numFiles": "*count"}';
        msi_json_arrayops(*rescNumFilesArray, *jsonArr, "add", 0);

        # Add the same values to the list object
        *rescIdList = cons(*resc, *rescIdList);
        *rescNumFilesList = cons(*count, *rescNumFilesList);
    }

    # Return the full json object as result
    *jsonStr = '';
    msiString2KeyValPair("", *kvp);
    msiAddKeyVal(*kvp, 'numFilesPerResc', *rescNumFilesArray);
    msi_json_objops(*jsonStr, *kvp, "set");
    *result = *jsonStr;

    # Also return as lists (for easy usage in other rules)
    *resultIdList = *rescIdList;
    *resultNumFilesList = *rescNumFilesList;

}

INPUT *collection=""
OUTPUT ruleExecOut