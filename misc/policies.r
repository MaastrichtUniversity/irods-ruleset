# Policies

acSetRescSchemeForCreate {
    if($objPath like "/nlmumc/projects/*/*") {
        *resource = "";

        uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);

        foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project") {
            if ( *av.META_COLL_ATTR_NAME == "resource" ) {
                *resource = *av.META_COLL_ATTR_VALUE;
            }
        }

        if ( *resource == "") {
            failmsg(-1, "resource is empty!");
        }

        msiWriteRodsLog("Setting resource for project *project to resource *resource", *status);

        msiSetDefaultResc(*resource, "forced");
    } else {
        msiSetDefaultResc("rootResc","null");
    }
}

acPostProcForPut {
    ### Policy to remove CIFS-ACL on metadata.xml ###
    if($objPath like "/nlmumc/ingest/zones/*/metadata.xml") {

        # Retrieve dropzone path
        uuChop($objPath, *dropzone, *tail, "/", false);
        uuChop(*dropzone, *head, *token, "/", false);

        # Retrieve ingestResource from the corresponding project
        getCollectionAVU(*dropzone,"project",*project,"","true");
        getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
        foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
            *ingestResourceHost = *r.RESC_LOC;
        }

        # Retrieve username of the ingest zone
        getCollectionAVU(*dropzone,"author",*user,"","true");

        # DEBUG statements
        # msiWriteRodsLog("Found new metadata xml file in $objPath", *status);
        # msiWriteRodsLog("dropzone is *dropzone", *status);
        # msiWriteRodsLog("token is *token", *status);
        # msiWriteRodsLog("project is *project", *status);
        # msiWriteRodsLog("user is *user", *status);
        # msiWriteRodsLog("ingestResource is *ingestResource", *status);
        # msiWriteRodsLog("ingestResourceHost is *ingestResourceHost", *status);

        remote(*ingestResourceHost,"") {
            msiExecCmd("metadata-acl-ro.sh", *user ++ " " ++ "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *status);
        }
    }
}
