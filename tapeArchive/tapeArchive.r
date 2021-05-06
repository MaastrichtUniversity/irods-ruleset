# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within prepareTapeArchive.r rule

tapeArchive(*archColl, *counter, *rescParentsLocation, *dataPerResources, *rescParentsName){
     *stateAttrName = "archiveState";

     # split the *archColl into *project and *projectCollection
     uuChopPath(*archColl, *dir, *projectCollection);
     uuChopPath(*dir, *dir2, *project);

     # Get the destination archive resource from the project
     getCollectionAVU("/nlmumc/projects/*project","archiveDestinationResource",*archiveResc,"N/A","true");

     foreach (*r in select RESC_LOC where RESC_NAME = '*archiveResc'){
        *archiveHostLocation = *r.RESC_LOC;
     }

    # Count how many file have been archived
    *isMoved=0;

    foreach(*srcResourceId in *rescParentsLocation) {
        # Get the coordinating resource name
        *coordResourceName = *rescParentsName.*srcResourceId;

        # Get the data array in *dataPerResources by the *coordResourceName
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, '*coordResourceName', '');
        msi_json_objops(*dataPerResources, *kvp, "get");
        *dataArray = *kvp.*coordResourceName;

        # Get the data array size
        *size = 0;
        msi_json_arrayops(*dataArray , "", "size", *size);

        # Get the resource host location
        *resourceHostLocation= *rescParentsLocation.*srcResourceId;

        if ( *size > 0 ){
            # Do a remote execution on *archiveHostLocation
            # remote(*archiveHostLocation,"") {
                for (*index=0; *index < *size; *index = *index + 1) {
                    # Get the data's path by its index in *dataArray
                    *dataPath = "";
                    msi_json_arrayops(*dataArray, *dataPath, "get", *index)
                    msiWriteRodsLog("DEBUG: *dataPath", 0);

                    # Update state AVU with progress
                    # Collection have been opened in prepareTapeArchive
                    # Otherwise update will failed
                    *value = "archive-in-progress "++str(*isMoved+1)++"/"++str(*counter);
                    setCollectionAVU(*archColl,*stateAttrName,*value);

                    # Calculate data checksum
                    # We do not pass any options, this way we get the existing checksum, or a new one is calculated.
                    # If a failure occurs, the replication is stopped, no trimming happens and we can manually verify
                    # any other replicas
                    msiDataObjChksum(*dataPath,"",*chksum);

                    # Replicate data from *coordResourceName to *archiveResc
                    # Checksum verification is implicit here, because we calculated the checksum already, msiDataObjRepl
                    # will automatically also include a checksum check on the destination
                    msiDataObjRepl(*dataPath, "destRescName=*archiveResc", *moveStatus);
                    if ( *moveStatus != 0 ) {
                       failmsg(-1, "Replication of *ipath from *coordResourceName to *archiveResc FAILED.");
                    }

                    # remote(*resourceHostLocation,"") {
                        # Trim data from *coordResourceName
                        msiDataObjTrim(*dataPath, *coordResourceName, "null", "1", "null", *trimStatus);
                        if ( *trimStatus != 1 ) {
                           failmsg(-1, "Trim *ipath from *coordResourceName FAILED.");
                        }

                        # Update counter
                        *isMoved=*isMoved+1;

                        # Report logs
                        msiWriteRodsLog("DEBUG: \t\tchksum done *chksum", 0);
                        msiWriteRodsLog("DEBUG: \t\trepl moveStat done *moveStatus", 0);
                        msiWriteRodsLog("DEBUG: \t\ttrim stat done *trimStatus", 0);
                        msiWriteRodsLog("DEBUG: \t\tReplicate from *coordResourceName to *archiveResc", 0);
                   # }
                #}
            }
        }
    }
    # Update state AVU to done
    setCollectionAVU(*archColl, *stateAttrName, "archive-done")
    msiWriteRodsLog("DEBUG: surfArchiveScanner archived *isMoved files ", 0);

    # Delete state AVU
    msiAddKeyVal(*delKV, *stateAttrName, "archive-done");
    msiRemoveKeyValuePairsFromObj(*delKV,*archColl, "-C");

    # Get project's id and collection's id
    uuChopPath(*archColl, *dir, *projectCollection);
    uuChopPath(*dir, *dir2, *project);

    # Re-calculate new values for dcat:byteSize and numFiles
    setCollectionSize(*project, *projectCollection, 'false', 'false');
    msiWriteRodsLog("DEBUG: dcat:byteSize and numFiles have been re-calculated and adjusted", 0);

    # Close collection by making all access read only
    closeProjectCollection(*project, *projectCollection);
}
