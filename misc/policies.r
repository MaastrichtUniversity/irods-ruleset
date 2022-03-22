# Policies

# Control the SSL requirements for iRODS-connections. The options are:
# "CS_NEG_REFUSE" for no SSL,
# "CS_NEG_REQUIRE" to demand SSL,
# "CS_NEG_DONT_CARE" to allow the server to decide
# Source: https://github.com/irods-contrib/metalnx-web/blob/master/docs/Getting-Started.md#setup-irods-negotiation
acPreConnect(*OUT) { *OUT="CS_NEG_REQUIRE"; }

acPostProcForPut {
    if($objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
        *resource = "";
        *sizeIngested = 0;
        uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);
        uuChop(*tail, *collection, *tail, "/", true);
        getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
        if( *resource == $rescName ) {
            foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project/*collection") {
                if ( *av.META_COLL_ATTR_NAME == "sizeIngested" ) {
                    *sizeIngested = double(*av.META_COLL_ATTR_VALUE);
                }
            }
            *sizeIngested = *sizeIngested + double($dataSize);
            msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
            msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
        }
    }
}

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
        }
    }

}

acPreprocForCollCreate {
    # msiGetSessionVarValue("all", "server")
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

}

acPostProcForCollCreate {
    ### Policy to increment the value of the 'latest_project_number' AVU on /nlmumc/projects ###
    if ($collName like regex "/nlmumc/projects/P[0-9]{9}") {
        *latest = 0;
        # Find out the current max project number
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects' ) {
            uuChopPath(*Row.COLL_NAME, *path, *c);
            *i = int(substr(*c, 1, 10));

            if ( *i > *latest ) {
                *latest = *i;
            }
        }
        msiAddKeyVal(*latestProjectNumberAVU, "latest_project_number", str(*latest));
        msiSetKeyValuePairsToObj(*latestProjectNumberAVU, "/nlmumc/projects", "-C");
    }
}

# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta add, adda, addw, set, rm, rmw, rmi
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) {
#    msiWriteRodsLog("DEBUG: ADD, SET, RM option kicked off", *status);

    ### Policy to prevent setting specials AVU by unauthorized users
    if(*AName == "responsibleCostCenter" || *AName == "enableArchive" || *AName == "enableUnarchive"
    || *AName == "enableOpenAccessExport" || *AName == "collectionMetadataSchemas" || *AName == "enableContributorEditMetadata") {
        # Get the value for the PI registered
        getCollectionAVU(*ItemName,"OBI:0000103",*pi,"","true");
        # Get the value for the Data Steward
        getCollectionAVU(*ItemName,"dataSteward",*dataSteward,"","true");
        # Get if the user is a part of the DH-project-admins group
        *isAdmin = ""
        get_user_admin_status($userNameClient, *isAdmin);

        if( $userNameClient == *pi || $userNameClient == *dataSteward || $userNameClient == "rods" || *isAdmin == "true") {
            # Do nothing and resume normal operation
            msiWriteRodsLog("INFO: [AUDIT_TRAIL] *ItemName: User $userNameClient sets '*AName' to '*AValue'", *status);
        }else{
            # Disallow setting the AVU
            msiWriteRodsLog("ERROR: [AUDIT_TRAIL] *ItemName: User $userNameClient is not allowed to set '*AName'", *status);
            cut;
            msiOprDisallowed;
        }
    }
}

# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta mod
# Note 1: Metalnx uses the 'mod'-option
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit, *NAName, *NAValue, *NAUnit) {
#    msiWriteRodsLog("DEBUG: MOD option kicked off", *status);

    ### Policy to prevent setting specials AVU by unauthorized users
    if(*AName == "responsibleCostCenter" || *AName == "enableArchive" || *AName == "enableUnarchive"
    || *AName == "enableOpenAccessExport" || *AName == "collectionMetadataSchemas" || *AName == "enableContributorEditMetadata") {
        # Get the value for the PI registered
        getCollectionAVU(*ItemName,"OBI:0000103",*pi,"","true");
        # Get the value for the Data Steward
        getCollectionAVU(*ItemName,"dataSteward",*dataSteward,"","true");
        # Get if the user is a part of the DH-project-admins group
        *isAdmin = ""
        get_user_admin_status($userNameClient, *isAdmin);

        if( $userNameClient == *pi || $userNameClient == *dataSteward || $userNameClient == "rods" || *isAdmin == "true") {
            # Do nothing and resume normal operation
            msiWriteRodsLog("INFO: [AUDIT_TRAIL] *ItemName: User $userNameClient sets '*AName' to '*AValue'", *status);
        }else{
            # Disallow setting the AVU
            msiWriteRodsLog("ERROR: [AUDIT_TRAIL] *ItemName: User $userNameClient is not allowed to set '*AName'", *status);
            cut;
            msiOprDisallowed;
        }
    }
}

# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta cp
acPreProcForModifyAVUMetadata(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName) {
#    msiWriteRodsLog("DEBUG: COPY option kicked off", *status);

    # This policy is currently not doing anything
}

# Enforce single threaded iRODS data connections when using Ceph S3 resources
# The arguments for msiSetNumThreads are:
# 1) sizePerThrInMb - integer value in MBytes to calculate the number of threads (default: 32)
# 2) maxNumThr      - the maximum number of threads to use (default: 4).
# 3) windowSize     - the tcp window size in Bytes for the parallel transfer (default: 1048576).
acSetNumThreads {
    # Session variables $rescName and $KVPairs are not always present and their existence needs to be checked first.
    # For instance, during replication it only exists for one of the two resources.
    # It errors, but doesn't affect the outcome of the replication.
    # Note: The ERROR is catched below and thus suppressed from the rodsLog

    *error = errorcode(msiGetValByKey($KVPairs,"rescName",*out));

    if ( *error == 0 ) {
        if ($KVPairs.rescName == "UM-Ceph-S3-AC" || $KVPairs.rescName == "UM-Ceph-S3-GL") {
            msiSetNumThreads("default","0","default");
        } else {
            msiSetNumThreads("default","16","default");
        }
    }
}
