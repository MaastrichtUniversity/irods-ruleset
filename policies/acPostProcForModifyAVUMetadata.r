# This PEP is triggered after AVUmetadata operations for data, collection, user and resources that are equivalent to the icommand:
# imeta add, adda, addw, set, rm, rmw, rmi
acPostProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) {
#    msiWriteRodsLog("DEBUG: ADD, SET, RM option kicked off", *status);

    # This policy modifies all dropzone ACLs for the project ID that was modified
    if(*AName == "enableDropzoneSharing" && *ItemName like regex "/nlmumc/projects/P[0-9]{9}") {
         uuChop(*ItemName, *head, *projectId, "/nlmumc/projects/", true);
         set_project_acl_to_dropzones(*projectId)
    }
}