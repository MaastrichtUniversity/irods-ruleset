# Fires before file creation
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

    ### Policy to prevent file creation directly in direct ingest folder ###
    if($objPath like regex "/nlmumc/ingest/direct/.*") {
        uuChopPath($objPath, *path, *c);
        if (*path == "/nlmumc/ingest/direct"){
            msiWriteRodsLog("DEBUG: No creating of files in root of /nlmumc/ingest/direct allowed. Path = $objPath by '$userNameClient'", *status);
            cut;
            msiOprDisallowed;
        } else {
            # The resource of anything created in /nlmumc/ingest/direct should always be stagingResc01
            msiSetDefaultResc("stagingResc01", "forced");
        }
    }

    ### Policy to prevent file creation directly in direct ingest folder ###
    if($objPath like regex "/nlmumc/ingest/zones/.*") {
        uuChopPath($objPath, *path, *c);
        if (*path == "/nlmumc/ingest/zones"){
            msiWriteRodsLog("DEBUG: No creating of files in root of /nlmumc/ingest/zones allowed. Path = $objPath by '$userNameClient'", *status);
            cut;
            msiOprDisallowed;
        } else {
            # The resource of anything created in /nlmumc/ingest/zones should always be stagingResc01
            msiSetDefaultResc("stagingResc01", "forced");
        }
    }

    ### Policy to restrict object creation during or after ingestion ###
    if($objPath like regex "/nlmumc/ingest/direct/.*/.*") {
        *state = "";
        uuChop($objPath, *basePath, *tail, "/nlmumc/ingest/direct/", true);
        uuChop(*tail, *token, *rest, "/", true);
        getCollectionAVU("/nlmumc/ingest/direct/*token","state",*state,"","false");
        *in_active_ingest = ""
        is_dropzone_state_in_active_ingestion(*state, *in_active_ingest)
        if(*in_active_ingest == "true") {
            msiWriteRodsLog("DEBUG: Object '$objPath' was not allowed to be created during dropzone state '*state' by '$userNameClient'", *status);
            cut;
            msiOprDisallowed;
        }
    }
}
