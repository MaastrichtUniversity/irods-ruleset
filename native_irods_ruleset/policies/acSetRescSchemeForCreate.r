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
        if($objPath like regex "^/nlmumc/home/rods/tmp.{6,8}demoResc$") {
            # setup_irods.py will test_put() a temporary file, we reroute to
            # demoResc instead of rootResc as the latter has not been created
            # yet at that stage. For iRES(es), setup_irods.py will mkresc its
            # default resource before doing test_put(). Only iCAT test file
            # ends in "demoResc".
            # See: https://github.com/irods/irods/blob/4.2.11/scripts/setup_irods.py#L145
            #      https://github.com/python/cpython/blob/v2.7/Lib/tempfile.py#L134 (python3 is 8!)
            # Note: ^ $ seem to be implicit anyway
            msiWriteRodsLog("acSetRescSchemeForCreate: iCAT setup_irods.py::test_put() detected '$objPath'", 0);
            msiSetDefaultResc("demoResc","null");
        } else {
            # For other files, we set rootResc as the default, as we did before.
            msiSetDefaultResc("rootResc","null");
        }
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

    ### Policy to prevent file creation directly in mounted ingest folder ###
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
