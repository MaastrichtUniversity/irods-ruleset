# This rule will calculate the number of files distributed over (multiple) coordinating resources
# E.g. 100 files on replRescUM01, 50 files on replRescUMCeph01
# Call with
#
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/misc/calcCollectionFilesAcrossResc.r "*collection='/nlmumc/projects/P000000001/C000000001'"
#
# Output:
# This rule outputs the same information both in json and iRODS list format

irule_dummy() {
    IRULE_calcCollectionFilesAcrossResc(*collection, *result, *resultIdList, *resultNumFilesList);
    writeLine("stdout", *result);
}

IRULE_calcCollectionFilesAcrossResc(*collection, *result, *resultIdList, *resultNumFilesList) {
    # Initialize variables
    *resources; # Key pair Value object to store resource type for each resource. key -> resource ID; value ->  "parent" or "orphan"    # Determine all resources used in this collection
    *rescNumFilesArray = '[]';
    *rescIdList = list();
    *rescNumFilesList = list();

    # Determine all this collection's resources and their parent/orphan type
    getResourcesInCollection(*collection, *resources);

    # Loop over the resources key-value object
    foreach ( *rescId in *resources ) {
        *count = 0;

        # Loop over all distinct files in in this collection-resource combination
        if ( *resources.*rescId == "parent" ) { # if the value of *rescId equals parent
            foreach ( *Row in SELECT DATA_ID WHERE COLL_NAME like "*collection%"  and RESC_PARENT = *rescId) {
                # not doing anything with the SQL result, just counting the number of iterations in the loop
                *count = *count + 1;
            }
        } else if ( *resources.*rescId == "orphan" ) { # if the value of *rescId equals orphan
            foreach ( *Row in SELECT DATA_ID WHERE COLL_NAME like "*collection%"  and RESC_ID = *rescId) {
                # not doing anything with the SQL result, just counting the number of iterations in the loop
                *count = *count + 1;
            }
        } else {
            failmsg(-1, "Error with determining storage resource type");
        }

        # Collect the values for this iteration and add it to the json array
        *jsonArr = '{"resourceID": "*rescId", "numFiles": "*count"}';
        json_arrayops_add(*rescNumFilesArray, *jsonArr, "");

        # Add the same values to the list object
        *rescIdList = cons(*rescId, *rescIdList);
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
