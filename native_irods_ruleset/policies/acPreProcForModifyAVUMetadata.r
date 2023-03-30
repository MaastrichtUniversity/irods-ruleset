# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta add, adda, addw, set, rm, rmw, rmi
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) {
#    msiWriteRodsLog("DEBUG: ADD, SET, RM option kicked off", *status);
    modifyProjectAVUMetadataPolicy(*ItemName,*AName,*AValue)
}

# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta mod
# Note 1: Metalnx uses the 'mod'-option
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit, *NAName, *NAValue, *NAUnit) {
#    msiWriteRodsLog("DEBUG: MOD option kicked off", *status);
    modifyProjectAVUMetadataPolicy(*ItemName,*AName,*AValue)
}

# This PEP is triggered with AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta cp
acPreProcForModifyAVUMetadata(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName) {
#    msiWriteRodsLog("DEBUG: COPY option kicked off", *status);

    # This policy is currently not doing anything
}

modifyProjectAVUMetadataPolicy(*ItemName,*AName,*AValue) {
    ### Policy to prevent setting specials Project AVU by unauthorized users
    if(*ItemName like regex "/nlmumc/projects/P[0-9]{9}") {
        if(*AName == "description" || *AName == "enableArchive" || *AName == "enableUnarchive"
        || *AName == "enableOpenAccessExport" || *AName == "collectionMetadataSchemas"
        || *AName == "enableContributorEditMetadata" || *AName == "enableDropzoneSharing") {
            msiCheckAccess(*ItemName,"own",*Result);
            *isAdmin = ""
            get_user_admin_status($userNameClient, *isAdmin);
            *authorized = 0
            if(*Result == 1 || $userNameClient == "rods" || *isAdmin == "true") {
                *authorized = 1
            }
            modifyProjectAVUMetadataController(*authorized,*ItemName,*AName,*AValue)
        }
        else if (*AName == "responsibleCostCenter") {
            # Get the value for the PI registered
            getCollectionAVU(*ItemName,"OBI:0000103",*pi,"","true");
            # Get the value for the Data Steward
            getCollectionAVU(*ItemName,"dataSteward",*dataSteward,"","true");
            # Get if the user is a part of the DH-project-admins group
            *isAdmin = ""
            get_user_admin_status($userNameClient, *isAdmin);
            *authorized = 0
            if( $userNameClient == *pi || $userNameClient == *dataSteward || $userNameClient == "rods" || *isAdmin == "true") {
                *authorized = 1
            }
            modifyProjectAVUMetadataController(*authorized,*ItemName,*AName,*AValue)
        }
    }
}

modifyProjectAVUMetadataController(*authorized,*ItemName,*AName,*AValue){
    if(*authorized == 1) {
        # Do nothing and resume normal operation
        *eventMessage = "*ItemName: User $userNameClient sets '*AName' to '*AValue'"
        *auditTrailMessage = ""
        format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
        msiWriteRodsLog("INFO: *auditTrailMessage", *status);
    } else {
        # Disallow setting the AVU
        *eventMessage = "*ItemName: User $userNameClient is not allowed to set '*AName'"
        *auditTrailMessage = ""
        format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
        msiWriteRodsLog("ERROR: *auditTrailMessage", *status);
        cut;
        msiOprDisallowed;
    }
}