# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within prepareTapeArchive.r rule

tapeArchive(*archColl, *initiator, *counter){
     *stateAttrName = "archiveState";

     # split the *archColl into *project and *projectCollection
     uuChopPath(*archColl, *dir, *projectCollection);
     uuChopPath(*dir, *dir2, *project);

     # Get the destination archive resource from the project
     getCollectionAVU("/nlmumc/projects/*project","archiveDestinationResource",*archiveResc,"N/A","true");

    # Count how many file have been archived
    *isMoved=0;

	msiWriteRodsLog("INFO: surfArchiveScanner found *counter files", 0);

    if (*counter > 0) {
        getResourcesNames(*rescParentsName);
        getDataPathToArchive(*archColl, *archiveResc, *dataPerResources, *rescParentsName);

        foreach(*dataPath in *dataPerResources) {
            *coordResourceName = *dataPerResources.*dataPath;

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
            msiWriteRodsLog("DEBUG: \t\tchksum done *chksum", 0);

            # Replicate data from *coordResourceName to *archiveResc
            # Checksum verification is implicit here, because we calculated the checksum already, msiDataObjRepl
            # will automatically also include a checksum check on the destination
            # 'errorcode()' catches the microservice's error, making it non-fatal, so that the rule continues processing and is able to 'setTapeErrorAVU()'
            *moveError = errorcode(msiDataObjRepl(*dataPath, "destRescName=*archiveResc", *moveStatus));
            msiWriteRodsLog("DEBUG: \t\t*dataPath -> moveError: *moveError", 0);
            if ( *moveError != 0 ) {
                setTapeErrorAVU(*archColl, *initiator, *stateAttrName, "error-archive-failed", "Replication of *dataPath from *coordResourceName to *archiveResc FAILED.")
            }

            # Trim data from *coordResourceName
            # 'errorcode()' catches the microservice's error, making it non-fatal, so that the rule continues processing and is able to 'setTapeErrorAVU()'
            *trimError = errorcode(msiDataObjTrim(*dataPath, *coordResourceName, "null", "1", "null", *trimStatus));
            msiWriteRodsLog("DEBUG: \t\t*dataPath -> trimError: *trimError", 0);
            if ( *trimError != 0 ) {
                setTapeErrorAVU(*archColl, *initiator, *stateAttrName, "error-archive-failed", "Trim *dataPath from *coordResourceName FAILED.")
            }

            # Update counter
            *isMoved=*isMoved+1;

            # Report logs
            msiWriteRodsLog("DEBUG: \t\tReplicate from *coordResourceName to *archiveResc", 0);
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

getResourcesNames(*rescParentsName){
    foreach (*r in select RESC_PARENT, RESC_LOC where RESC_LOC != 'EMPTY_RESC_HOST'){
        *resourceParentId = *r.RESC_PARENT;

        if (*resourceParentId != ""){
            # Query the resource parent name by its ID
            foreach (*p in select RESC_NAME where RESC_ID = *resourceParentId ){
                *coordResourceName = *p.RESC_NAME;
                *rescParentsName.*resourceParentId = *coordResourceName;
            }
        }
    }
}

getDataPathToArchive(*archColl, *archiveResc, *dataPerResources, *rescParentsName){
    # The minimum file size criteria (in bytes)
    *minimumSize=262144000;

	foreach( *ScanColl in
            SELECT
                RESC_PARENT,
                COLL_NAME,
                DATA_NAME
            WHERE
                COLL_NAME like '*archColl%'
                AND DATA_RESC_NAME != '*archiveResc'
                AND DATA_SIZE >= '*minimumSize'){
        # Build data full path
        *dataPath = *ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

        # Get the coordinating resource name
        *resourceParentId = *ScanColl.RESC_PARENT;
        *coordResourceName = *rescParentsName.*resourceParentId;

        *dataPerResources.*dataPath = *coordResourceName

	}
    msiWriteRodsLog("DEBUG: dataPerResources: *dataPerResources", 0);
}
