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
            *eventMessage = "*ItemName: User $userNameClient sets '*AName' to '*AValue'"
            *auditTrailMessage = ""
            format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
            msiWriteRodsLog("INFO: *auditTrailMessage", *status);
        }else{
            # Disallow setting the AVU
            *eventMessage = "*ItemName: User $userNameClient is not allowed to set '*AName'"
            *auditTrailMessage = ""
            format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
            msiWriteRodsLog("ERROR: *auditTrailMessage", *status);
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
            *eventMessage = "*ItemName: User $userNameClient modifies '*AName' to '*AValue'"
            *auditTrailMessage = ""
            format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
            msiWriteRodsLog("INFO: *auditTrailMessage", *status);
        }else{
            # Disallow setting the AVU
            *eventMessage = "*ItemName: User $userNameClient is not allowed to modify '*NAValue'"
            *auditTrailMessage = ""
            format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
            msiWriteRodsLog("ERROR: *auditTrailMessage", *status);
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