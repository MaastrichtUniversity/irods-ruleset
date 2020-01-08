# This rule will (re)calculate and set the total size and numFiles of a collection (folder) in iRODS
# This is useful in cases where the size of a collection has changed due to deletion or addition of files.
#
# Call with
#
# irule -F setCollectionSize.r "*project='P000000001'" "*projectCollection='C000000001'" "*openPC='true'" "*closePC='true'"


irule_dummy() {
    IRULE_setCollectionSize(*project, *projectCollection, *openPC, *closePC);
}

IRULE_setCollectionSize(*project, *projectCollection, *openPC, *closePC) {
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
        msiWriteRodsLog("setCollectionSize: Starting for *dstColl", 0);

        # Open Collection
        if ( *openPC == "true" ) {
            msiWriteRodsLog("setCollectionSize: Opening *dstColl", 0);
            # We only need to open the collection, and not all the files in it. So use msiSetACL directly instead of openProjectCollection rule
            msiSetACL("default", "admin:own", "rods", "/nlmumc/projects/*project/*projectCollection");
        }

        # Calculate the number of files and total size of the ProjectCollection
        calcCollectionSize(*dstColl, "B", "ceiling", *size);
        calcCollectionFiles(*dstColl, *numFiles);

        # Collect information in multiple key-values
        ### Simple KVs ###
        msiAddKeyVal(*metaKV, "dcat:byteSize", str(*size));
        msiAddKeyVal(*metaKV, "numFiles", str(*numFiles));

        ### Block for byteSizes and numFiles across resources ###
        # Remove all pre-existing resource related AVUs from collection. We don't want to leave artefact AVUs for resources that are not in use anymore.
        *execDel = 0;
        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*dstColl" ) {
            # Check for pre-existing AVUs and collect them in a Key-Value construct
            if ( *av.META_COLL_ATTR_NAME like regex "dcat:byteSize_resc_([0-9])+" ) {
                *attribute = *av.META_COLL_ATTR_NAME;
                *value = *av.META_COLL_ATTR_VALUE;
                #  Remove this AVU from collection
                msiWriteRodsLog("setCollectionSize: Removing pre-existing AVU *attribute", 0);
                msiAddKeyVal(*delKV, *attribute, *value );
                *execDel = *execDel + 1;
            }
            if ( *av.META_COLL_ATTR_NAME like regex "numFiles_resc_([0-9])+" ) {
                *attribute = *av.META_COLL_ATTR_NAME;
                *value = *av.META_COLL_ATTR_VALUE;
                #  Remove this AVU from collection
                msiWriteRodsLog("setCollectionSize: Removing pre-existing AVU *attribute", 0);
                msiAddKeyVal(*delKV, *attribute, *value );
                *execDel = *execDel + 1;
            }
        }
        # Batch removal of the collected AVUs
        if (*execDel > 0) {
            msiRemoveKeyValuePairsFromObj(*delKV, *dstColl, "-C");
        }

        # Calculate the number of files and total size across all resources in this ProjectCollection
        calcCollectionSizeAcrossResc(*dstColl, "B", "ceiling", *rescSizeArray, *rescIdsSize, *rescSizings);
        calcCollectionFilesAcrossResc(*dstColl, *rescNumFilesArray, *rescIdsNumFiles, *rescNumFiles);

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
        if ( *closePC == "true" ) {
            msiWriteRodsLog("setCollectionSize: Closing *dstColl", 0);
            # We only need to close the collection in a non-recursive fashion, so use msiSetACL directly
            msiSetACL("default", "read", "rods", "/nlmumc/projects/*project/*projectCollection");
        }

        msiWriteRodsLog("setCollectionSize: Finished for *dstColl", 0);

    } else {
        failmsg(-1, "Error in setCollectionSize: projectCollection *dstColl does not exist");
    }

}

INPUT *project="",*projectCollection="",*openPC="true",*closePC="true"
OUTPUT ruleExecOut