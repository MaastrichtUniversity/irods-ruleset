createIngest {
   *tokenColl = *ingestMount ++ "/" ++ *token;

    msiExecCmd("enable-ingest-zone.sh", *user ++ " /mnt/ingest/" ++ *token, "null", "null", "null", *OUT);
    msiCollCreate(*tokenColl, 0, *OUT);
    msiPhyPathReg(*tokenColl, "nfsResc", "/mnt/ingest/" ++ *token, "mountPoint", *status);

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "machine", *machine);
    msiAssociateKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

    msiSetACL("default", "own", *user, *tokenColl)
}


ingest {

    msiAddKeyVal(*metaKV, "state", "ingesting");
    msiAssociateKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    delay("<PLUSET>1s</PLUSET>") {
         msiCollRsync(*srcColl, *dstColl, "nfsResc", "IRODS_TO_IRODS", *status);
    
         # TODO: Handle errors
         *code = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

          msiAddKeyVal(*metaKV, "state", "ingested");
          msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

          delay("<PLUSET>1m</PLUSET>") {
               msiRmColl(*srcColl, "forceFlag=", *OUT);
          }
     }
}
