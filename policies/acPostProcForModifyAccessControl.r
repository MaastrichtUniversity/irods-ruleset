# This policy is triggered after ACLs have been modified:
acPostProcForModifyAccessControl(*RecursiveFlag,*AccessLevel,*UserName,*Zone,*Path) {
    if(*AccessLevel != "read" && *Path like regex "/nlmumc/projects/P[0-9]{9}") {
        uuChop(*Path, *head, *projectId, "/nlmumc/projects/", true);
        transfer_project_acl_to_dropzone_single(*projectId, *UserName)
    }
}