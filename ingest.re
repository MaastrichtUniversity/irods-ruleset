ingest {
    writeLine("stdout", "Start ingesting " ++ *srcColl ++ " to " ++ *dstColl);

    *err=errorcode(msiObjStat(*srcColl,*out));
    if ( *err==0 ) {
        writeLine("stdout", "Source does not exist");
    } else {

        msiCollRsync(*srcColl, *dstColl, "nfsResc", "IRODS_TO_IRODS", *Status);

        msiRmColl(*srcColl, "forceFlag=", *Status);

        writeLine("stdout", "Finished ingesting");
    }
}

INPUT *srcColl="", *dstColl=""
OUTPUT ruleExecOut
