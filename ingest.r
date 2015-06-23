ingest {
    writeLine("stdout", "Start ingesting " ++ *srcColl ++ " to " ++ *dstColl);

    msiCollRsync(*srcColl, *dstColl, "nfsResc", "IRODS_TO_IRODS", *Status);

    msiRmColl(*srcColl, "forceFlag=", *Status);

    writeLine("stdout", "Finished ingesting");
}

INPUT *srcColl="", *dstColl=""
OUTPUT ruleExecOut
