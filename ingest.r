# Call with
#
# irule -F ingest.r "*token='creepy-click'"

ingest {
    *srcColl = /nlmumc/ingestZone/*token;

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        failmsg(-814000, "Unknown token");
    }

    *project = ""; *department = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
         if ( *av.META_COLL_ATTR_NAME == "project" ) {
             *project = *av.META_COLL_ATTR_VALUE;
         }
         if ( *av.META_COLL_ATTR_NAME == "department" ) {
             *department = *av.META_COLL_ATTR_VALUE;
         }
    }

    *resource = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project") {
         if ( *av.META_COLL_ATTR_NAME == "resource" ) {
             *resource = *av.META_COLL_ATTR_VALUE;
         }
    }

    if ( *resource == "") {
         failmsg(-1, "resource is empty!");
    }
    if ( *project == "" ) {
         *project = "no-project";
    }
    if ( *department == "" ) {
         *department = "no-department";
    }

    msiGetIcatTime(*dateTime, "unix");
    *dateUser = *dateTime ++ "_" ++ $userNameClient;

    # TODO: Do something with department
    *dstColl = /nlmumc/projects/*project/*dateUser;

    msiAddKeyVal(*metaKV, "state", "ingesting");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    msiWriteRodsLog("Ingesting *srcColl to *dstColl with resource: *resource", *status);

    delay("<PLUSET>1s</PLUSET>") {
         msiCollRsync(*srcColl, *dstColl, *resource, "IRODS_TO_IRODS", *status);
    
         # TODO: Handle errors
         *code = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

         msiAddKeyVal(*metaKV, "state", "ingested");
         msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

         delay("<PLUSET>1m</PLUSET>") {
              msiRmColl(*srcColl, "forceFlag=", *OUT);
              msiExecCmd("disable-ingest-zone.sh", "/mnt/ingestZone/" ++ *token, "null", "null", "null", *OUT);
         }
     }
}

INPUT *token=""
OUTPUT ruleExecOut
