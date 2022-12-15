
tapeUnArchiveFile(*ScanColl, *archiveResc, *projectResource, *resourceLocation, *isMoved, *count){
    # TODO After 4.2.6 update, check replication performance without remote call
    remote(*resourceLocation,""){

        *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

        *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
        setCollectionAVU(*archColl, "archiveState",*value);

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
