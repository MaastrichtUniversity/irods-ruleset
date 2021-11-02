# Call with
#
# irule -F createProject.r "*authorizationPeriodEndDate='1-1-2018'" "*dataRetentionPeriodEndDate='1-1-2018'" "*ingestResource='iresResource'" "*resource='replRescUM01'" "*storageQuotaGb='10'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*dataSteward='d.steward@maastrichtuniversity.nl'" "*respCostCenter='UM-30001234X'" "*openAccess='false'" "*tapeArchive='true'" "*tapeUnarchive='true'"

irule_dummy() {
    IRULE_createProject(*result,*authorizationPeriodEndDate,*dataRetentionPeriodEndDate,*ingestResource,*resource,*storageQuotaGb,*title,*principalInvestigator,*dataSteward,*respCostCenter,*openAccess,*tapeArchive,*tapeUnarchive);
    writeLine("stdout", *result);
}


# Creates projects in the form P000000001
IRULE_createProject(*project,*authorizationPeriodEndDate,*dataRetentionPeriodEndDate,*ingestResource,*resource,*storageQuotaGb,*title,*principalInvestigator,*dataSteward,*respCostCenter,*openAccess,*tapeArchive,*tapeUnarchive) {

    *retry = 0;
    *error = -1;

    # Try to create the dstColl. Exit the loop on success (error = 0) or after too many retries.
    # The while loop adds compatibility for usage in parallellized runs of the delayed rule engine.
    while ( *error < 0 && *retry < 10) {

        getCollectionAVU("/nlmumc/projects","latest_project_number",*latest,"","true");
        *new_latest = int(*latest) + 1;
        *project = str(*new_latest);

        # Prepend padding zeros to the name
        while ( strlen(*project) < 9 ) {
            *project = "0" ++ *project;
        }

        *project = "P" ++ *project;

        *dstColl = "/nlmumc/projects/*project";

        *retry = *retry + 1;
        *error = errorcode(msiCollCreate(*dstColl, 0, *status));

    }

    # Make the rule fail if it doesn't succeed in creating the project
    if ( *error < 0 && *retry >= 10 ) {
        failmsg(*error, "Collection '*title' attempt no. *retry : Unable to create *dstColl");
    }

    # Set the new latest_project_number AVU
    msiAddKeyVal(*latestProjectNumberAVU, "latest_project_number", str(*new_latest));
    msiSetKeyValuePairsToObj(*latestProjectNumberAVU, "/nlmumc/projects", "-C");

    # TODO: Determine whether setting defaults here is a good place
    msiAddKeyVal(*metaKV, "authorizationPeriodEndDate", *authorizationPeriodEndDate);
    msiAddKeyVal(*metaKV, "dataRetentionPeriodEndDate", *dataRetentionPeriodEndDate);
    msiAddKeyVal(*metaKV, "ingestResource", *ingestResource);
    msiAddKeyVal(*metaKV, "resource", *resource);
    msiAddKeyVal(*metaKV, "storageQuotaGb", *storageQuotaGb);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "OBI:0000103", *principalInvestigator);
    msiAddKeyVal(*metaKV, "dataSteward", *dataSteward);
    msiAddKeyVal(*metaKV, "responsibleCostCenter", *respCostCenter);
    msiAddKeyVal(*metaKV, "enableOpenAccessExport", *openAccess);
    msiAddKeyVal(*metaKV, "enableArchive", *tapeArchive);
    msiAddKeyVal(*metaKV, "enableUnarchive", *tapeUnarchive);
    # TODO Make it compatible with multiple archive resources.
    *archiveDestResc = "";
    # Look-up for the resource set as the archive destination resource
    foreach (*av in SELECT RESC_NAME WHERE META_RESC_ATTR_NAME="archiveDestResc" AND META_RESC_ATTR_VALUE="true") {
        *archiveDestResc = *av.RESC_NAME;
    }
    if (*archiveDestResc == "") {
        failmsg(-1, "ERROR: The attribute 'archiveDestResc' has no value in iCAT");
    }
    msiAddKeyVal(*metaKV, "archiveDestinationResource", *archiveDestResc);

    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");

    # Set recursive permissions
    msiSetACL("default", "write", "service-pid", *dstColl);
    msiSetACL("default", "read", "service-disqover", *dstColl);
    msiSetACL("recursive", "inherit", "", *dstColl);
    # If the user calling this function is someone other than 'rods' (so a project admin)
    # we need to add rods as a owner on this project and remove the person calling this method
    # from the ACLs
    if ($userNameClient != "rods") {
        msiSetACL("default", "own", "rods", *dstColl);
        msiSetACL("default", "null", $userNameClient, *dstColl);
    }

}

INPUT *authorizationPeriodEndDate="", *dataRetentionPeriodEndDate="", *ingestResource="", *resource="", *storageQuotaGb="", *title="", *principalInvestigator="", *dataSteward="", *respCostCenter="", *openAccess="", *tapeArchive="", *tapeUnarchive=""
OUTPUT ruleExecOut
