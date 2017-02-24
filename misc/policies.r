# Policies

acSetRescSchemeForCreate {
    ### Policy to set proper storage resource & prevent file creation directly in P-folder ###
    # Since 'acPreProcForCreate' does not fire in iRODS 4.1.x, we made 'acSetRescSchemeForCreate' a combined policy
    if($objPath like regex "/nlmumc/projects/P[0-9]{9}/.*") {
        if($objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
            # This is a proper location to store project files
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

            msiWriteRodsLog("DEBUG: Setting resource for project *project to resource *resource", *status);
            msiSetDefaultResc(*resource, "forced");
        } else {
            # Somebody tries to create a file outside of a projectcollection
            uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
            uuChop(*tail, *project, *tail, "/", true);

            msiWriteRodsLog("DEBUG: Not allowed to create files in projecfolder '*project' for objPath '$objPath'", *status);
            cut;
            msiOprDisallowed;
        }
    } else {
        # We are not in a projectfolder at all
        msiSetDefaultResc("rootResc","null");
    }
}

acPreprocForCollCreate {
    ### Policy to regulate folder creation within projects ###
    if($collName like regex "/nlmumc/projects/P[0-9]{9}/.*") {
        if( ! ($collName like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}" || $collName like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*")) {
            # Creating a non-C folder at project level
            msiWriteRodsLog("DEBUG: Folder '$collName' not compliant with naming convention", *status);
            cut;
            msiOprDisallowed;
        }
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
