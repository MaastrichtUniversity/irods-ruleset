# Call with
# irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /rules/native_irods_ruleset/tapeArchive/prepareTapeArchive.r "*archColl='/nlmumc/projects/P000000006/C000000001'" "*initiator='jmelius'"

irule_dummy() {
    IRULE_prepareTapeArchive(*archColl, *initiator);
}

IRULE_prepareTapeArchive(*archColl, *initiator) {
    # split the *archColl into *project and *projectCollection
    uuChopPath(*archColl, *dir, *projectCollection);
    uuChopPath(*dir, *dir2, *project);

    # Check if the TapeArchive feature is enabled of the project
    getCollectionAVU("/nlmumc/projects/*project","enableArchive",*enableArchive,"false","false");
    if (*enableArchive == "false") {
        failmsg(-1, "ERROR: The TapeArchive feature is not enable for the project '*project'");
    }

    # Get the destination archive resource from the project
    getCollectionAVU("/nlmumc/projects/*project","archiveDestinationResource",*archiveResc,"N/A","true");
    # The minimum file size criteria (in bytes)
    *minimumSize=262144000;
    # rodsadmin user running the rule
    # get this from avu set on archive
    getResourceAVU(*archiveResc,"service-account",*aclChange,"N/A","true");
    # state AVU attribute name -> to report progress
    *stateAttrName = "archiveState";

    # Log statements
    msiWriteRodsLog("INFO: Archival workflow started for *archColl", 0);
    msiWriteRodsLog("DEBUG: Data will be moved to resource *archiveResc", 0);
    msiWriteRodsLog("DEBUG: Service account used is *aclChange", 0);
    msiWriteRodsLog("DEBUG: *initiator is the initiator", 0);

    # Query *stateAttrName value
    *stateValue = "";
    foreach (*av in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = "*archColl" AND META_COLL_ATTR_NAME in ("'archiveState', 'unArchiveState'")) {
        *stateValue = *av.META_COLL_ATTR_VALUE;
    }
    # Check for valid state to start archiving
    if ( *stateValue != "" ) {
        failmsg(-1, "Invalid state to start archiving.");
    }

    # Get project's id and collection's id
    uuChopPath(*archColl, *dir, *projectCollection);
    uuChopPath(*dir, *dir2, *project);
    # Open collection to modify state AVU
    openProjectCollection(*project, *projectCollection, *aclChange, 'own');

    # count the number of files that match the criteria
    *counter=0;

    # Get each data that match the criteria to will be replicated at *archiveResc
    # And add *dataPath to *dataArray in *dataPerResources on the *coordResourceName key
    # WARNING regex % wont work with C00001.1
	foreach( *ScanColl in
            SELECT
                RESC_PARENT,
                COLL_NAME,
                DATA_NAME
            WHERE
                COLL_NAME like '*archColl%'
                AND DATA_RESC_NAME != '*archiveResc'
                AND DATA_SIZE >= '*minimumSize'){

        *counter=*counter+1;
	}

    *value = "Number of files found: *counter";
    setCollectionAVU(*archColl, "archiveState", *value)

    # Delay before replication
    delay("<PLUSET>1s</PLUSET><INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
	    msiWriteRodsLog("INFO: prepareTapeArchive found *counter files to archive", 0);
        tapeArchive(*archColl, *initiator, *counter);
    }
}

INPUT *archColl="", *initiator=""
OUTPUT ruleExecOut