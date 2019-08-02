# Call with
#
# irule -F createProject.r "*authorizationPeriodEndDate='1-1-2018'" "*dataRetentionPeriodEndDate='1-1-2018'" "*ingestResource='iresResource'" "*resource='replRescUM01'" "*storageQuotaGb='10'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*respCostCenter='UM-30001234X'"

irule_dummy() {
    IRULE_createProject(*result,*authorizationPeriodEndDate,*dataRetentionPeriodEndDate,*ingestResource,*resource,*storageQuotaGb,*title,*principalInvestigator,*respCostCenter);
    writeLine("stdout", *result);
}


# Creates projects in the form P000000001
IRULE_createProject(*project,*authorizationPeriodEndDate,*dataRetentionPeriodEndDate,*ingestResource,*resource,*storageQuotaGb,*title,*principalInvestigator,*respCostCenter) {

    *retry = 0;
    *error = -1;

    # Try to create the dstColl. Exit the loop on success (error = 0) or after too many retries.
    # The while loop adds compatibility for usage in parallellized runs of the delayed rule engine.
    while ( *error < 0 && *retry < 10) {

        *max = 0;

        # Find out the current max project number
        foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '/nlmumc/projects' ) {
            uuChopPath(*Row.COLL_NAME, *path, *c);

            *i = int(substr(*c, 1, 10));

            if ( *i > *max ) {
                *max = *i;
            }
        }

        *project = str(*max + 1);

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

    # TODO: Determine whether setting defaults here is a good place
    msiAddKeyVal(*metaKV, "authorizationPeriodEndDate", *authorizationPeriodEndDate);
    msiAddKeyVal(*metaKV, "dataRetentionPeriodEndDate", *dataRetentionPeriodEndDate);
    msiAddKeyVal(*metaKV, "ingestResource", *ingestResource);
    msiAddKeyVal(*metaKV, "resource", *resource);
    msiAddKeyVal(*metaKV, "storageQuotaGb", *storageQuotaGb);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "OBI:0000103", *principalInvestigator);
    msiAddKeyVal(*metaKV, "responsibleCostCenter", *respCostCenter);
    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");


    # Set recursive permissions
    msiSetACL("default", "read", "service-dwh", *dstColl);
    msiSetACL("default", "write", "service-pid", *dstColl);
    msiSetACL("default", "read", "service-disqover", *dstColl);
    msiSetACL("recursive", "inherit", "", *dstColl);

}

INPUT *authorizationPeriodEndDate="", *dataRetentionPeriodEndDate="", *ingestResource="", *resource="", *storageQuotaGb="", *title="", *principalInvestigator="", *respCostCenter=""
OUTPUT ruleExecOut