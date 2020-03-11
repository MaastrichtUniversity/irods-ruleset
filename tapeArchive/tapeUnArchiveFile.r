
tapeUnArchiveFile(*ScanColl, *archiveResc, *projectResource, *resourceLocation, *isMoved, *count){
    # TODO After 4.2.6 update, check replication performance without remote call
    remote(*resourceLocation,""){

        *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

        *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
        setCollectionAVU(*archColl, "archiveState",*value);

        msiDataObjChksum(*ipath,"verifyChksum=",*chksum);
        msiWriteRodsLog("DEBUG: surfArchiveScanner archived file *ipath", 0);

        msiDataObjRepl(*ipath, "destRescName=*projectResource++++verifyChksum=", *moveStatus);
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
