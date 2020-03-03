
tapeUnArchiveFile(*ScanColl, *archiveResc, *projectResource, *resourceLocation, *isMoved, *count){
    # TODO After 4.2.6 update, check replication performance without remote call
    remote(*resourceLocation,""){

        *ipath=*ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

        *value = "unarchive-in-progress "++str(*isMoved+1)++"/"++str(*count);
        setCollectionAVU(*archColl, "archiveState",*value);

        msiDataObjChksum(*ipath,"verifyChksum=",*chksum);
        writeLine("serverLog", "surfArchiveScanner archived file "++*ipath);

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
        writeLine("serverLog", "\t\tiCAT checksum "++str(*ScanColl.DATA_CHECKSUM));
        writeLine("serverLog", "\t\tchksum done "++str(*chksum));
        writeLine("serverLog", "\t\trepl moveStat done "++str(*moveStatus));
        writeLine("serverLog", "\t\ttrim stat done "++str(*trimStatus));
        writeLine("serverLog", "\t\tsurfArchiveScanner found "++str(*ipath));
        writeLine("serverLog", "\t\tReplicate from "++*archiveResc++" to "++*projectResource);
    }
}
