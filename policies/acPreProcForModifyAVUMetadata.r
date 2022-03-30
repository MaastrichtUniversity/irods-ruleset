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