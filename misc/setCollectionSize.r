# This rule will (re)calculate and set the total size of a collection (folder) in iRODS
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

        # Add multiple AVUs to ProjectCollection
        #msiWriteRodsLog("DEBUG: Setting 'dcat:byteSize' to *size", 0);
        #msiWriteRodsLog("DEBUG: Setting 'numFiles' to *numFiles", 0);
        msiAddKeyVal(*metaKV, "dcat:byteSize", str(*size));
        msiAddKeyVal(*metaKV, "numFiles", str(*numFiles));
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