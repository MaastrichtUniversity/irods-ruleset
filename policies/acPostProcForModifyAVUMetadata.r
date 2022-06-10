# This PEP is triggered after AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta add, adda, addw, set, rm, rmw, rmi
acPostProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) {
#    msiWriteRodsLog("DEBUG: ADD, SET, RM option kicked off", *status);
    if(*AName == "enableDropzoneSharing" && *ItemName like regex "/nlmumc/projects/P[0-9]{9}") {
         uuChop(*ItemName, *head, *projectId, "/nlmumc/projects/", true);
         *eventMessage = "*ItemName: User $userNameClient sets '*AName' to '*AValue'"
         *auditTrailMessage = ""
         format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
         msiWriteRodsLog("INFO: *auditTrailMessage", *status);
         transfer_project_acl_to_dropzone(*projectId, "false")
    }
}