# Policies

acSetRescSchemeForCreate {
    ### Policy to set proper storage resource & prevent file creation directly in P-folder ###
    # Since 'acPreProcForCreate' does not fire in iRODS 4.1.x, we made 'acSetRescSchemeForCreate' a combined policy
    if($objPath like regex "/nlmumc/projects/P[0-9]{9}/.*") {

        # We're testing here for both "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*" and "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}".
        # The second test will allow objects to be created at project level with the form  C[0-9]{9}
        # This is a workaround for a bug where msiPhyPathReg() first tries to create an object when registering a collection
        # This workaround can be removed once we start using msiTarFileExtract() in untarProjectCollection.r

        if($objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*" || $objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}") {
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
    ### Policy to send new HL7CDA files for MDL to MirthConnect ###
    if($objPath like "/nlmumc/projects/P000000010/C000000001/*.xml") {
        msi_getenv("MIRTH_MDL_EXPORT_CHANNEL", *mirthMdlURL);

        #msiWriteRodsLog("DEBUG: Send MDL data to url *mirthMdlURL", 0);
        *error = errorcode(msi_http_send_file("*mirthMdlURL", "$objPath"));

        if ( *error < 0 ) {
            failmsg(-1, "Error with sending to MDL MirthC channel *mirthMdlURL");
        }
    }
}
