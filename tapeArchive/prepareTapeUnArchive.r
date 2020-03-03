# Call with
# irule -F prepareTapeUnArchive.r "*archColl='/nlmumc/projects/P000000017/C000000001'"

irule_dummy() {
    IRULE_prepareTapeUnArchive(*archColl);
}

IRULE_prepareTapeUnArchive(*archColl) {

    # TODO Improve regex path sanity check
    if (*archColl like regex '/nlmumc/projects/P.*/C.*'){
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

    # Get the destination archive resource from the project
    getCollectionAVU("/nlmumc/projects/*project","archiveDestinationResource",*resc,"N/A","true");
    # rodsadmin user running the rule
    # get this from avu set on archive
    getResourceAVU(*resc,"service-account",*aclChange,"N/A","true");
    *stateAttrName = "archiveState";

    # Retrieve archiveState
    *archiveState = "";
    foreach (*av in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME == "*archColl" AND META_COLL_ATTR_NAME == "archiveState") {
        *archiveState = *av.META_COLL_ATTR_VALUE;
    }

    # Check for valid state to start archiving
    if ( *archiveState != "no-state-set" && *archiveState != "archive-done"  && *archiveState != ""
            && *archiveState not like  "Number of files offline:*"  && *archiveState not like  "Caching files countdown:*") {
        failmsg(-1, "Invalid state(*archiveState) to start process.");
    }

    *dmfs_attr;
    *count;

    #Find our resource location (FQDN)
    foreach(*r in SELECT RESC_LOC WHERE RESC_NAME = *resc){
        *svr=*r.RESC_LOC;
    }
    writeLine("serverLog", "\nConnecting on *resc - *svr");

    msiGetObjType(*archColl, *inputType);
    if (*inputType like '-d'){
         writeLine("serverLog", "Checking data status: *archColl");
        *count = checkTapeFile(*resc, *svr, *archColl, *dmfs_attr, *dataPathList);
    }
    if (*inputType like '-c'){
        writeLine("serverLog", "Checking collection status: *archColl");
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
        writeLine("serverLog", "Stage back to cache: *offlineList");

        # Recursive call to check un-migrating status
        prepareTapeUnArchive(*archColl);
    }

    # UnMigrating Check
    if (*unMigratingList != ""){
        writeLine("serverLog", "Un-migrating to cache: *unMigratingList");
        *value = "Caching files countdown: *unMigratingCounter";
        setCollectionAVU(*projectCollectionPath, *stateAttrName, *value)

        # Delay & recursive call
        delay("<PLUSET>30s</PLUSET>"){
            writeLine("serverLog", "SURFSara Archive - delay 30s, before retry");
            prepareTapeUnArchive(*archColl);
        }
    }
    else{
        # UnArchive Check
        if (*unArchivingList != ""){
            *value = "start-transfer";
            setCollectionAVU(*projectCollectionPath, *stateAttrName, *value)
            writeLine("serverLog", "Start replication back to UM for: *unArchivingList ");
            delay("<PLUSET>1s</PLUSET>") {
                tapeUnArchive(*count, *archColl);
            }
        }
        else{
            writeLine("serverLog", "Nothing to un-archive");
        }
    }
}

INPUT *archColl=""
OUTPUT ruleExecOut