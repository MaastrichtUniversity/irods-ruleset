# Call with
#
# irule -F ingest.r "*token='creepy-click'"

ingest {
    *srcColl = /nlmumc/ingestZone/*token;

    if (errorcode(msiObjStat(*srcColl,*out)) < 0) {
        failmsg(-814000, "Unknown ingest zone *token");
    }

    *project = ""; *title = "";
    foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "*srcColl") {
        if ( *av.META_COLL_ATTR_NAME == "project" ) {
            *project = *av.META_COLL_ATTR_VALUE;
        }
        if ( *av.META_COLL_ATTR_NAME == "title" ) {
            *title = *av.META_COLL_ATTR_VALUE;
        }
    }

    if ( *project == "" ) {
        failmsg(-1, "project is empty!");
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

    createProjectCollection(*project, *dstColl);

    msiAddKeyVal(*metaKV, "state", "ingesting");
    msiSetKeyValuePairsToObj(*metaKV, *srcColl, "-C");

    msiWriteRodsLog("Ingesting *srcColl to *dstColl on resource: *resource", *status);

    delay("<PLUSET>1s</PLUSET>") {
        msiCollRsync(*srcColl, *dstColl, *resource, "IRODS_TO_IRODS", *status);

        # Close collection by making all access read only
        closeProjectCollection(*dstColl);


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
