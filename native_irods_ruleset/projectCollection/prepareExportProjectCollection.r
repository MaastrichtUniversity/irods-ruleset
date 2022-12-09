
# Call with
# irule -s -F prepareExportProjectCollection.r  *collection='C000000001' *repository='Dataverse'
#
# This rule creates an AVU called 'exporterState'
# Make sure to call this rule as 'rodsadmin' because it will open a collection using admin-mode.

irule_dummy() {
    IRULE_prepareExportProjectCollection(*project, *collection, *repository);
}

IRULE_prepareExportProjectCollection(*project, *collection, *repository){
    getCollectionAVU("/nlmumc/projects/*project","enableOpenAccessExport",*enableOpenAccessExport,"false","false");
    if (*enableOpenAccessExport == "false") {
        failmsg(-1, "ERROR: The OpenAccessExport feature is not enable for the project '*project'");
    }

    # Open collection to modify state AVU
    openProjectCollection(*project, *collection, 'rods', 'own');

    # Create state AVU
    *status = *repository ++ ":in-queue-for-export";
    msiAddKeyVal(*metaKV, "exporterState", *status);
    msiAssociateKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
}


INPUT *project='', *collection='', *repository=''
OUTPUT ruleExecOut