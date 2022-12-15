# This policy is triggered after ACLs have been modified:
acPostProcForModifyAccessControl(*RecursiveFlag,*AccessLevel,*UserName,*Zone,*Path) {
    # This policy modifies all dropzone ACLs for the project ID that was modified
    if(*Path like regex "/nlmumc/projects/P[0-9]{9}") {
        uuChop(*Path, *head, *projectId, "/nlmumc/projects/", true);
        *eventMessage = "*Path: User $userNameClient sets '*UserName' to '*AccessLevel'"
        *auditTrailMessage = ""
        format_audit_trail_message($userNameClient, *eventMessage, *auditTrailMessage);
        msiWriteRodsLog("INFO: *auditTrailMessage", *status);
        set_single_user_project_acl_to_dropzones(*projectId, *UserName)
    }
}
