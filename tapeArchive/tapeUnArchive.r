
tapeUnArchive(*count, *archColl){
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

    # rodsadmin user running the rule
    # get this from avu set on archive
    getResourceAVU(*archiveResc,"service-account",*aclChange,"N/A","true");

    *isMoved=0;                 #Number of files moved counter
    *stateAttrName = "archiveState";

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

    #Find our resource location
    *resourceLocation = ""
    foreach(*parent in SELECT RESC_ID WHERE RESC_NAME = *projectResource){
        *parentID = *parent.RESC_ID;
        foreach(*r in SELECT RESC_LOC WHERE RESC_PARENT = *parentID){
            *resourceLocation = *r.RESC_LOC;
        }
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
            remote(*resourceLocation,""){
                *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

                *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
                setCollectionAVU(*projectCollectionPath, "archiveState",*value);

                # We do not pass any options, this way we get the existing checksum, which should always exist for
                # archived files. If a failure occurs, the replication is stopped, no trimming happens
                msiDataObjChksum(*ipath,"",*chksum);
                msiWriteRodsLog("DEBUG: surfArchiveScanner archived file *ipath", 0);

                # Checksum verification is implicit here, because we calculated the checksum already, msiDataObjRepl
                # will automatically also include a checksum check on the destination
                msiDataObjRepl(*ipath, "destRescName=*projectResource", *moveStatus);
                if ( *moveStatus != 0 ) {
                       failmsg(-1, "Replication of *ipath from *coordResourceName to *archiveResc FAILED.");
                }

                msiDataObjTrim(*ipath, *archiveResc, "null", "1", "null", *trimStatus);
                if ( *trimStatus != 1 ) {
                       failmsg(-1, "Trim *ipath from *coordResourceName FAILED.");
                }

                *isMoved=*isMoved+1;
                # Debug
                msiWriteRodsLog("DEBUG: \t\tiCAT checksum *ScanColl.DATA_CHECKSUM" , 0);
                msiWriteRodsLog("DEBUG: \t\tchksum done *chksum", 0);
                msiWriteRodsLog("DEBUG: \t\trepl moveStat done *moveStatus", 0);
                msiWriteRodsLog("DEBUG: \t\ttrim stat done *trimStatus", 0);
                msiWriteRodsLog("DEBUG: \t\tsurfArchiveScanner found *ipath", 0);
                msiWriteRodsLog("DEBUG: \t\tReplicate from *archiveResc to *projectResource", 0);
            }
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
            remote(*resourceLocation,""){
                *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

                *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
                setCollectionAVU(*projectCollectionPath, "archiveState",*value);

                # We do not pass any options, this way we get the existing checksum, which should always exist for
                # archived files. If a failure occurs, the replication is stopped, no trimming happens
                msiDataObjChksum(*ipath,"",*chksum);
                msiWriteRodsLog("DEBUG: surfArchiveScanner archived file *ipath", 0);

                # Checksum verification is implicit here, because we calculated the checksum already, msiDataObjRepl
                # will automatically also include a checksum check on the destination
                msiDataObjRepl(*ipath, "destRescName=*projectResource", *moveStatus);
                if ( *moveStatus != 0 ) {
                       failmsg(-1, "Replication of *ipath from *coordResourceName to *archiveResc FAILED.");
                }

                msiDataObjTrim(*ipath, *archiveResc, "null", "1", "null", *trimStatus);
                if ( *trimStatus != 1 ) {
                       failmsg(-1, "Trim *ipath from *coordResourceName FAILED.");
                }

                *isMoved=*isMoved+1;
                # Debug
                msiWriteRodsLog("DEBUG: \t\tiCAT checksum *ScanColl.DATA_CHECKSUM" , 0);
                msiWriteRodsLog("DEBUG: \t\tchksum done *chksum", 0);
                msiWriteRodsLog("DEBUG: \t\trepl moveStat done *moveStatus", 0);
                msiWriteRodsLog("DEBUG: \t\ttrim stat done *trimStatus", 0);
                msiWriteRodsLog("DEBUG: \t\tsurfArchiveScanner found *ipath", 0);
                msiWriteRodsLog("DEBUG: \t\tReplicate from *archiveResc to *projectResource", 0);
            }
        }
    }
    # Update state AVU to done
    *value = "unarchive-done";
    setCollectionAVU(*projectCollectionPath, "archiveState",*value)
    msiWriteRodsLog("DEBUG: surfArchiveScanner found *isMoved files", 0);

    # Delete status AVU
    msiAddKeyVal(*delKV, *stateAttrName, *value);
    msiRemoveKeyValuePairsFromObj(*delKV,*projectCollectionPath, "-C");

    # Re-calculate new values for dcat:byteSize and numFiles
    setCollectionSize(*project, *projectCollection, 'false', 'false');
    msiWriteRodsLog("DEBUG: dcat:byteSize and numFiles have been re-calculated and adjusted", 0);


    # Close collection by making all access read only
    closeProjectCollection(*project, *projectCollection);
}