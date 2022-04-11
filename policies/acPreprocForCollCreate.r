# Gets fired before collection creation
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

    ### Policy to regulate folder creation within direct ingest ###
    if($collParentName == "/nlmumc/ingest/direct") {
        # Allow rods-admin to create folders
        if (! ($userNameClient == "rods")){
            # Allow the creation of folder trough python-irodsclient (MDR)
            if ( !($connectOption == "python-irodsclient")){
                    msiWriteRodsLog("DEBUG: Folder '$collName' was not allowed to be created in /nlmumc/ingest/direct/ by '$userNameClient'", *status);
                    cut;
                    msiOprDisallowed;
            }
        }
    }

    ### Policy to restrict folder creation of .metadata_versions inside of a dropzone ###
    if($collName like regex "/nlmumc/ingest/direct/.*/.metadata_versions") {
        msiWriteRodsLog("DEBUG: Folder '$collName' was not allowed to be created by '$userNameClient'", *status);
        cut;
        msiOprDisallowed;
    }

    ### Policy to restrict folder creation during or after ingestion ###
    if($collName like regex "/nlmumc/ingest/direct/.*/.*") {
        *state = "";
        uuChop($collName, *basePath, *tail, "/nlmumc/ingest/direct/", true);
        uuChop(*tail, *token, *rest, "/", true);
        getCollectionAVU("/nlmumc/ingest/direct/*token","state",*state,"","false");
        if(*state != "open" && *state != "warning-validation-incorrect" && *state != "error-post-ingestion" && *state != "error-ingestion") {
            msiWriteRodsLog("DEBUG: Folder '$collName' was not allowed to be created during dropzone state '*state' by '$userNameClient'", *status);
            cut;
            msiOprDisallowed;
        }
    }
}