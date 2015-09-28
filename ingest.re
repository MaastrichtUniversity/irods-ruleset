createIngest {
    *tokenColl = /ritZone/ingest/*token;

    *code = errorcode(msiCollCreate(*tokenColl, 0, *status));

    if ( *code == -809000 ) {
        failmsg(-1, "Token already in use");
    } else if ( *code != 0 ) {
        fail(*code);
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "machine", *machine);
    msiAssociateKeyValuePairsToObj(*metaKV, "*tokenColl", "-C");

    msiExecCmd("enable-ingest-zone.sh", *user ++ " /mnt/ingest/" ++ *token, "null", "null", "null", *status);
    msiPhyPathReg(*tokenColl, "nfsResc", /mnt/ingest/*token, "mountPoint", *status);

    msiSetACL("default", "own", *user, *tokenColl)
}

ingest {
    *srcColl = /ritZone/ingest/*token;

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        failmsg(-814000, "Unknown token");
    }

    *project = ""; *machine = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
         if ( *av.META_COLL_ATTR_NAME == "project" ) {
             *project = *av.META_COLL_ATTR_VALUE;
         }
         if ( *av.META_COLL_ATTR_NAME == "machine" ) {
             *machine = *av.META_COLL_ATTR_VALUE;
         }
    }

    if ( *project == "" ) {
         *project = "projectless";
    }
    if ( *machine == "" ) {
         *machine = "machineless";
    }

    *dstColl = /ritZone/m4i-nanoscopy/*project/*machine;

    msiAddKeyVal(*metaKV, "state", "ingesting");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    msiWriteRodsLog("Ingesting *srcColl to *dstColl", *status);

    delay("<PLUSET>1s</PLUSET>") {
         msiCollRsync(*srcColl, *dstColl, "nfsResc", "IRODS_TO_IRODS", *status);
    
         # TODO: Handle errors
         *code = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

         msiAddKeyVal(*metaKV, "state", "ingested");
         msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

         delay("<PLUSET>1m</PLUSET>") {
              msiRmColl(*srcColl, "forceFlag=", *OUT);
              msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/" ++ *token, "null", "null", "null", *OUT);
         }
     }
}
