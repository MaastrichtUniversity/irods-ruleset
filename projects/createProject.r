# Call with
#
# irule -F createProject.r "*authorizationPeriodEndDate='1-1-2018'" "*dataRetentionPeriodEndDate='1-1-2018'" "*ingestResource='iresResource'" "*resource='replRescUM01'" "*storageQuotaGb='10'" "*title='Testing'" "*principalInvestigator='p.rofessor@maastrichtuniversity.nl'" "*respCostCenter='UM-30001234X'" "*pricePerGiBPerYear='0.32'"

irule_dummy() {
    IRULE_createProject(*result,*authorizationPeriodEndDate,*dataRetentionPeriodEndDate,*ingestResource,*resource,*storageQuotaGb,*title,*principalInvestigator,*respCostCenter,*pricePerGiBPerYear);
    writeLine("stdout", *result);
}


# Creates projects in the form P000000001
IRULE_createProject(*project,*authorizationPeriodEndDate,*dataRetentionPeriodEndDate,*ingestResource,*resource,*storageQuotaGb,*title,*principalInvestigator,*respCostCenter,*pricePerGiBPerYear) {

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

    msiCollCreate(*dstColl, 0, *status);

    # TODO: Determine whether setting defaults here is a good place
    msiAddKeyVal(*metaKV, "authorizationPeriodEndDate", *authorizationPeriodEndDate);
    msiAddKeyVal(*metaKV, "dataRetentionPeriodEndDate", *dataRetentionPeriodEndDate);
    msiAddKeyVal(*metaKV, "ingestResource", *ingestResource);
    msiAddKeyVal(*metaKV, "resource", *resource);
    msiAddKeyVal(*metaKV, "storageQuotaGb", *storageQuotaGb);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "OBI:0000103", *principalInvestigator);
    msiAddKeyVal(*metaKV, "responsibleCostCenter", *respCostCenter);
    msiAddKeyVal(*metaKV, "NCIT:C88193", *pricePerGiBPerYear);
    msiSetKeyValuePairsToObj(*metaKV, *dstColl, "-C");


    # Set recursive permissions
    msiSetACL("default", "read", "service-dwh", *dstColl);
    msiSetACL("default", "write", "service-pid", *dstColl);
    msiSetACL("default", "read", "service-disqover", *dstColl);
    msiSetACL("recursive", "inherit", "", *dstColl);
    
}

INPUT *authorizationPeriodEndDate="", *dataRetentionPeriodEndDate="", *ingestResource="", *resource="", *storageQuotaGb="", *title="", *principalInvestigator="", *respCostCenter="", *pricePerGiBPerYear=""
OUTPUT ruleExecOut