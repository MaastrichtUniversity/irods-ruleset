# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within prepareTapeUnArchive.r rule

tapeUnArchive(*count, *archColl, *initiator){
    #Matthew Saum
    #SURFsara b.v
    #2019
    #This version is for 4.2

     # TODO Improve regex path sanity check
     if (*archColl like regex '/nlmumc/projects/P.*/C.*'){
         # split the *archColl into *project and *projectCollection
         *splitPath =  split(*archColl, "/");
         *project = elem(*splitPath,2);
         *projectPath =  "/nlmumc/projects/*project";
         *projectCollection = elem(*splitPath,3);
         *projectCollectionPath = "/nlmumc/projects/*project/*projectCollection";
     }
     else{
         failmsg(-1, "Invalid input path: *archColl");
     }

     # Get the destination archive resource from the project
     getCollectionAVU(*projectPath,"archiveDestinationResource",*archiveResc,"N/A","true");

    *minimumSize=262144000;        #The minimum file size (in bytes)
    *isMoved=0;                 #Number of files moved counter
    *stateAttrName = "unArchiveState";

    msiWriteRodsLog("DEBUG: surfArchiveScanner found *count files", 0);

    msiGetObjType(*archColl, *inputType);
    if (*inputType like '-d'){
        uuChopPath(*archColl, *dir, *dataName);
        *archColl = *dir;
    }

    # Get projectResource AVU - replicate destination resource name
    *projectResource = "";
    foreach (*av in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME == "*projectPath" AND META_COLL_ATTR_NAME == "resource") {
        *projectResource = *av.META_COLL_ATTR_VALUE;
    }

    if (*inputType like '-d'){
        foreach(*ScanColl in
               SELECT
                      COLL_NAME,
                      DATA_NAME,
                      DATA_CHECKSUM
               WHERE
                      COLL_NAME = '*archColl'
                  AND DATA_NAME = '*dataName'
                  AND DATA_RESC_NAME = '*archiveResc'
        ){
            *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

            *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
            setCollectionAVU(*projectCollectionPath, *stateAttrName, *value);

            # We do not pass any options, this way we get the existing checksum, which should always exist for
            # archived files. If a failure occurs, the replication is stopped, no trimming happens
            msiDataObjChksum(*ipath,"",*chksum);
            msiWriteRodsLog("DEBUG: surfArchiveScanner archived file *ipath", 0);

            # Checksum verification is implicit here, because we calculated the checksum already, msiDataObjRepl
            # will automatically also include a checksum check on the destination
            # 'errorcode()' catches the microservice's error, making it non-fatal, so that the rule continues processing and is able to 'setTapeErrorAVU()'
            *moveError = errorcode(msiDataObjRepl(*ipath, "destRescName=*projectResource", *moveStatus));
            msiWriteRodsLog("DEBUG: \t\t*ipath -> moveError: *moveError", 0);
            if ( *moveError != 0 ) {
                   setTapeErrorAVU(*projectCollectionPath, *initiator, *stateAttrName, "error-unarchive-failed", "Replication of *ipath from *projectResource to *archiveResc FAILED.")
            }

            # 'errorcode()' catches the microservice's error, making it non-fatal, so that the rule continues processing and is able to 'setTapeErrorAVU()'
            *trimError = errorcode(msiDataObjTrim(*ipath, *archiveResc, "null", "1", "null", *trimStatus));
            msiWriteRodsLog("DEBUG: \t\t*ipath -> trimError: *trimError", 0);
            if ( *trimError != 0 ) {
                   setTapeErrorAVU(*projectCollectionPath, *initiator, *stateAttrName, "error-unarchive-failed", "Trim *ipath from *projectResource FAILED.")
            }

            *isMoved=*isMoved+1;
            # Debug
            msiWriteRodsLog("DEBUG: \t\tiCAT checksum *ScanColl.DATA_CHECKSUM" , 0);
            msiWriteRodsLog("DEBUG: \t\tchksum done *chksum", 0);
            msiWriteRodsLog("DEBUG: \t\tsurfArchiveScanner found *ipath", 0);
            msiWriteRodsLog("DEBUG: \t\tReplicate from *archiveResc to *projectResource", 0);
        }
    }

    # Recursively stage a collection
    if (*inputType like '-c'){
        foreach(*ScanColl in
               SELECT
                      COLL_NAME,
                      DATA_NAME,RESC_LOC,
                      DATA_CHECKSUM
               WHERE
                      COLL_NAME = '*archColl' || like '*archColl/%'
                  AND DATA_RESC_NAME = '*archiveResc'
        ){
            *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

            *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
            setCollectionAVU(*projectCollectionPath, *stateAttrName, *value);

            # We do not pass any options, this way we get the existing checksum, which should always exist for
            # archived files. If a failure occurs, the replication is stopped, no trimming happens
            msiDataObjChksum(*ipath,"",*chksum);
            msiWriteRodsLog("DEBUG: surfArchiveScanner archived file *ipath", 0);

            # Checksum verification is implicit here, because we calculated the checksum already, msiDataObjRepl
            # will automatically also include a checksum check on the destination
            # 'errorcode()' catches the microservice's error, making it non-fatal, so that the rule continues processing and is able to 'setTapeErrorAVU()'
            *moveError = errorcode(msiDataObjRepl(*ipath, "destRescName=*projectResource", *moveStatus));
            msiWriteRodsLog("DEBUG: \t\t*ipath -> moveError: *moveError", 0);
            if ( *moveError != 0 ) {
                   setTapeErrorAVU(*projectCollectionPath, *initiator, *stateAttrName, "error-unarchive-failed", "Replication of *ipath from *projectResource to *archiveResc FAILED.")
            }

            # 'errorcode()' catches the microservice's error, making it non-fatal, so that the rule continues processing and is able to 'setTapeErrorAVU()'
            *trimError = errorcode(msiDataObjTrim(*ipath, *archiveResc, "null", "1", "null", *trimStatus));
            msiWriteRodsLog("DEBUG: \t\t*ipath -> trimError: *trimError", 0);
            if ( *trimError != 0 ) {
                   setTapeErrorAVU(*projectCollectionPath, *initiator, *stateAttrName, "error-unarchive-failed", "Trim *ipath from *projectResource FAILED.")
            }

            *isMoved=*isMoved+1;
            # Debug
            msiWriteRodsLog("DEBUG: \t\tiCAT checksum *ScanColl.DATA_CHECKSUM" , 0);
            msiWriteRodsLog("DEBUG: \t\tchksum done *chksum", 0);
            msiWriteRodsLog("DEBUG: \t\tsurfArchiveScanner found *ipath", 0);
            msiWriteRodsLog("DEBUG: \t\tReplicate from *archiveResc to *projectResource", 0);
        }
    }
    # Update state AVU to done
    *value = "unarchive-done";
    setCollectionAVU(*projectCollectionPath, *stateAttrName, *value)
    msiWriteRodsLog("DEBUG: surfArchiveScanner found *isMoved files", 0);

    # Delete status AVU
    msiAddKeyVal(*delKV, *stateAttrName, *value);
    msiRemoveKeyValuePairsFromObj(*delKV,*projectCollectionPath, "-C");

    # Re-calculate new values for dcat:byteSize and numFiles
    setCollectionSize(*project, *projectCollection, 'false', 'false');
    msiWriteRodsLog("DEBUG: dcat:byteSize and numFiles have been re-calculated and adjusted", 0);


    # Close collection by making all access read only
    close_project_collection(*project, *projectCollection);
}
