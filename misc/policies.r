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


# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta add, adda, addw, set, rm, rmw, rmi
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) {
#    msiWriteRodsLog("DEBUG: ADD, SET, RM option kicked off", *status);

    ### Policy to prevent setting 'responsibleCostCenter' AVU by unauthorized users
    if(*AName == "responsibleCostCenter") {
        # Get the value for the PI registered
        getCollectionAVU(*ItemName,"OBI:0000103",*pi,"","true");

        if( $userNameClient == *pi || $userNameClient == "rods") {
            # Do nothing and resume normal operation
        }else{
            # Disallow setting the AVU
            msiWriteRodsLog("ERROR: User $userNameClient is not allowed to set *AName AVU", *status);
            cut;
            msiOprDisallowed;
        }
    }
}

# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta mod
# Note 1: Metalnx uses the 'mod'-option
# Note 2: There is a bug in Metalnx version 1.0-258 which is triggering this PEP randomly (i.e. PEP is not triggered on every edit operation). Confirmed that policy works as intended when using Metalnx version 2.0.0
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit, *NAName, *NAValue, *NAUnit) {
#    msiWriteRodsLog("DEBUG: MOD option kicked off", *status);

    ### Policy to prevent setting 'responsibleCostCenter' AVU by unauthorized users
    if(*AName == "responsibleCostCenter") {
        # Get the value for the PI registered
        getCollectionAVU(*ItemName,"OBI:0000103",*pi,"","true");

        if( $userNameClient == *pi || $userNameClient == "rods") {
            # Do nothing and resume normal operation
        }else{
            # Disallow setting the AVU
            msiWriteRodsLog("ERROR: User $userNameClient is not allowed to set *AName AVU", *status);
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
    if ($KVPairs.rescName == "UM-Ceph-S3-AC" || $KVPairs.rescName == "UM-Ceph-S3-GL") {
        msiSetNumThreads("default","0","default");
    } else {
        msiSetNumThreads("default","16","default");
    }
}
