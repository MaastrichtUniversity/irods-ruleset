# This rule will (re)calculate and set the total size and numFiles of a collection (folder) in iRODS
# This is useful in cases where the size of a collection has changed due to deletion or addition of files.
#
# Call with
#
# irule -F setCollectionSize.r "*project='P000000001'" "*projectCollection='C000000001'"


irule_dummy() {
    IRULE_setCollectionSize(*project, *projectCollection);
}

IRULE_setCollectionSize(*project, *projectCollection) {
    *size = "0";
    *numFiles = "0";
    *dstColl = "/nlmumc/projects/*project/*projectCollection"

    # Check if *dstColl exists (= length of collName in SQL result > 0)
    *collName = ""
    foreach ( *Row in SELECT COLL_NAME where COLL_NAME = *dstColl ) {
        *collName = *Row.COLL_NAME
    }

    # If the collection exists, we can calculate and set the collection size. Otherwise, we fail with error message
    if ( strlen(*collName) > 0 ) {
        msiWriteRodsLog("Start operation 'setCollectionSize' for *dstColl", 0);

        # Open Collection
        openProjectCollection(*project, *projectCollection, 'rods' , 'own');

        # Calculate the number of files and total size of the ProjectCollection
        calcCollectionSize(*dstColl, "B", "ceiling", *size);
        calcCollectionFiles(*dstColl, *numFiles);

        # Collect information in multiple key-values
        ### Simple KVs ###
        msiAddKeyVal(*metaKV, "dcat:byteSize", str(*size));
        msiAddKeyVal(*metaKV, "numFiles", str(*numFiles));

        ### Block for byteSizes and numFiles across resources ###
        # Calculate the number of files and total size across all resources in this ProjectCollection
        calcCollectionSizeAcrossCoordResources(*dstColl, "B", "ceiling", *rescSizeArray, *rescIdsSize, *rescSizings);
        calcCollectionFilesAcrossCoordResources(*dstColl, *rescNumFilesArray, *rescIdsNumFiles, *rescNumFiles);

        # Retrieve the byteSizes and numFiles for each resource
        # iRODS rule language doesn't have a proper for-loop. Implemented this using 'while'
        *i = 0;
        while (*i <= size(*rescIdsSize)-1) {
            msiAddKeyVal(*metaKV, "dcat:byteSize_resc_" ++ elem(*rescIdsSize, *i), str(elem(*rescSizings, *i)));
            *i = *i + 1;
        }

        *j = 0;
        while (*j <= size(*rescIdsNumFiles)-1) {
            msiAddKeyVal(*metaKV, "numFiles_resc_" ++ elem(*rescIdsNumFiles, *j), str(elem(*rescNumFiles, *j)));
            *j = *j + 1;
        }
        ### End of block ###

        # Set all key-values as AVUs to ProjectCollection
        msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");

        # Close collection by making all access read only
        closeProjectCollection(*project, *projectCollection);

        msiWriteRodsLog("Finished operation 'setCollectionSize' for *dstColl", 0);

    } else {
        failmsg(-1, "Error when setting CollectionSize: projectCollection *dstColl does not exist");
    }

}

INPUT *project="",*projectCollection=""
OUTPUT ruleExecOut