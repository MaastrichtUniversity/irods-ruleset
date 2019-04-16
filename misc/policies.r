# Policies

### Policy to set destination resources for projectCollections ###
acSetRescSchemeForCreate {
    if( $objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*" ) {
        uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);

        getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");

        # Check if we are actually performing a replication
        *replCheck="false";
        errorcode( *replCheck = temporaryStorage.inRepl );

        if (*replCheck == 'false') {
            msiWriteRodsLog("DEBUG: Setting resource for project *project to resource *resource", *status);
            msiSetDefaultResc("UM-hnas-4k","forced")
        }
    } else {
        # We are not in a projectCollection
        msiSetDefaultResc("rootResc","null");
    }
}

### Policy to set destination resource for replication of projectCollections ###
acSetRescSchemeForRepl {
    if( $objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*" ) {
        uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);

        getCollectionAVU("/nlmumc/projects/*project","replResource",*resource,"","true");

        # Signal to other rules that we're in replication
        temporaryStorage.inRepl = "true"

        msiWriteRodsLog("DEBUG: Setting replication resource for project *project to resource *resource.", *status);

        # TODO: Allow for replication to other resources such as the tape archive.
        msiSetDefaultResc(*resource,"forced")
    } else {
        # We are not in a projectCollection
        msiSetDefaultResc("rootResc","null");
    }
}

### Policy to prevent file creation directly in P-collection ###
pep_resource_create_pre(*instance, *comm, *context) {
    *path = *comm.logical_path;

    if( (*path like regex "/nlmumc/projects/P[0-9]{9}/.*") && ! (*path like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") ) {
        msiWriteRodsLog("ERROR: Not allowed to create objects directly in project at '*path'", *status);
        cut;
        msiOprDisallowed;
    }
}

### Policy to prevent file renaming into P-collection ###
pep_resource_rename_pre(*instance, *comm, *context, *new) {
   *path = *comm.logical_path;

   if( (*path like regex "/nlmumc/projects/P[0-9]{9}/.*") && ! (*path like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") ) {
       msiWriteRodsLog("ERROR: Not allowed to rename objects directly in project at '*path'", *status);
       cut;
       msiOprDisallowed;
   }
}

### Policy to prevent invalidly named collection creation directly in P-collection ###
acPreprocForCollCreate {
    ### Policy to regulate folder creation within projects ###
    if($collName like regex "/nlmumc/projects/P[0-9]{9}/.*" && !( $collName like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}") && !( $collName like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") ) {
        # Creating a non-C folder at project level
        msiWriteRodsLog("ERROR: Invalid naming of collection in project '$collName'", *status);
        cut;
        msiOprDisallowed;
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
