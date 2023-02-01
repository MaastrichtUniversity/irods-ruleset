# This rule handles two input variables: a collection absolute path or data object absolute path
# e.g Bring back an entire collection online
# irule -F prepareTapeUnArchive.r "*archColl='/nlmumc/projects/P000000017/C000000001'"
#
# e.g Bring back a single data object online
# irule -F prepareTapeUnArchive.r "*archColl='/nlmumc/projects/P000000017/C000000001/data/test/300MiB.log'"

irule_dummy() {
    IRULE_prepareTapeUnArchive(*archColl);
}

IRULE_prepareTapeUnArchive(*archColl) {

    # Check the input absolute path and initialize the required variables for this rule
    if (*archColl like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}.*"){
        # split the *archColl into *project and *projectCollection
        *splitPath =  split(*archColl, "/");
        *project = elem(*splitPath,2);
        *projectPath =  "/nlmumc/projects/*project";
        *projectCollection = elem(*splitPath,3);
        *projectCollectionPath = "/nlmumc/projects/*project/*projectCollection";
    }
    else{
         failmsg(-1, "Invalid input path: *archColl");
    }

    getCollectionAVU("/nlmumc/projects/*project","enableArchive",*enableArchive,"false","false");
    getCollectionAVU("/nlmumc/projects/*project","enableUnarchive",*enableUnarchive,*enableArchive,"false");
    if (*enableUnarchive != 'true') {
         failmsg(-1, "ERROR: Unarchiving is not allowed for project '*project'");
    }

    # Get the destination archive resource from the project
    getCollectionAVU("/nlmumc/projects/*project","archiveDestinationResource",*resc,"N/A","true");
    # rodsadmin user running the rule
    # get this from avu set on archive
    getResourceAVU(*resc,"service-account",*aclChange,"N/A","true");
    *stateAttrName = "unArchiveState";

     # Log statements
     msiWriteRodsLog("INFO: UnArchival worklow started for *archColl", 0);
     msiWriteRodsLog("DEBUG: Data will be moved from resource *resc", 0);
     msiWriteRodsLog("DEBUG: Service account used is *aclChange", 0);

    # Retrieve archiveState
    *archiveState = "";
    foreach (*av in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = "*archColl" AND META_COLL_ATTR_NAME in ("'archiveState', 'unArchiveState'")) {
        *archiveState = *av.META_COLL_ATTR_VALUE;
    }

    # Check for valid state to start archiving
    if ( *archiveState != "") {
        failmsg(-1, "Invalid state(*archiveState) to start process.");
    }

    *dmfs_attr;
    *count;

    #Find our resource location (FQDN)
    foreach(*r in SELECT RESC_LOC WHERE RESC_NAME = *resc){
        *svr=*r.RESC_LOC;
    }
    msiWriteRodsLog("DEBUG: Connecting on *resc - *svr", 0);

    msiGetObjType(*archColl, *inputType);
    if (*inputType like '-d'){
        msiWriteRodsLog("DEBUG: Checking data status: *archColl", 0);
        *count = checkTapeFile(*resc, *svr, *archColl, *dmfs_attr, *dataPathList);
    }
    if (*inputType like '-c'){
        msiWriteRodsLog("DEBUG: Checking collection status: *archColl", 0);
        *count = checkTapeCollection(*resc, *svr, *archColl, *dmfs_attr, *dataPathList);
    }

    # Open collection to update status AVU *archiveState
    openProjectCollection(*project, *projectCollection, *aclChange, 'own');

    *unMigratingCounter = 0;
    *offlineList = "";
    *unMigratingList  = "";
    *unArchivingList  = "";

    # Check if data list is not empty -> if true some data can be un-archived
    if (*dataPathList !=  ""){
        *value = "Number of files offline: *count";
        setCollectionAVU(*projectCollectionPath, *stateAttrName, *value)

        # Loop into the result key pair value: path -> status
        foreach(*path in *dmfs_attr){
             # Check if data are offline
            if ( *dmfs_attr.*path == "OFL"){
                if (*offlineList == ""){
                    *offlineList = *path;
                }
                else{
                    *offlineList = *offlineList++" "++*path;
                }
            }
            if ( *dmfs_attr.*path == "UNM"){
                 *unMigratingCounter =  *unMigratingCounter + 1;
                if (*unMigratingList == ""){
                    *unMigratingList = *path;
                }
                else{
                    *unMigratingList = *unMigratingList++" "++*path;
                }
            }
            if ( *dmfs_attr.*path == "DUL" || *dmfs_attr.*path == "REG" || *dmfs_attr.*path == "MIG"){
                if (*unArchivingList == ""){
                    *unArchivingList = *path;
                }
                else{
                    *unArchivingList = *unArchivingList++" "++*path;
                }
            }
        }
    }

    if (*offlineList != ""){
        # Call dmget to stage data back to cache
        dmget(*offlineList, *svr)
        msiWriteRodsLog("DEBUG: Stage back to cache: *offlineList", 0);

        # Recursive call to check un-migrating status
        prepareTapeUnArchive(*archColl);
    }

    # UnMigrating Check
    if (*unMigratingList != ""){
        msiWriteRodsLog("DEBUG: Un-migrating to cache: *unMigratingList", 0);
        *value = "Caching files countdown: *unMigratingCounter";
        setCollectionAVU(*projectCollectionPath, *stateAttrName, *value)

        # Delay & recursive call
        delay("<PLUSET>30s</PLUSET>"){
            msiWriteRodsLog("DEBUG: SURFSara Archive - delay 30s, before retry", 0);
            prepareTapeUnArchive(*archColl);
        }
    }
    else{
        # UnArchive Check
        if (*unArchivingList != ""){
            *value = "start-transfer";
            setCollectionAVU(*projectCollectionPath, *stateAttrName, *value)
            msiWriteRodsLog("DEBUG: Start replication back to UM for: *unArchivingList", 0);
            delay("<PLUSET>1s</PLUSET>") {
                tapeUnArchive(*count, *archColl);
            }
        }
        else{
            msiWriteRodsLog("DEBUG: Nothing to un-archive", 0);
        }
    }
}

INPUT *archColl=""
OUTPUT ruleExecOut
