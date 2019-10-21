# Call with
# irule -F prepareTapeUnArchive.r "*archColl='/nlmumc/projects/P000000017/C000000001'"


prepareTapeUnArchive {
    *aclChange="service-surfarchive";        #a rodsadmin group/user running the rule
    *stateAttrName = "archiveState";

    # Retrieve archiveState
    *archiveState = "";
    foreach (*av in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME == "*archColl" AND META_COLL_ATTR_NAME == "archiveState") {
        *archiveState = *av.META_COLL_ATTR_VALUE;
    }

    # Check for valid state to start archiving
    if ( *archiveState != "no-state-set" && *archiveState != "archive-done"  && *archiveState != "") {
        failmsg(-1, "Invalid state(*archiveState) to start process.");
    }

    *resc = "arcRescSURF01";
    *dmfs_attr;
    *count;

    #Find our resource location (FQDN)
    foreach(*r in SELECT RESC_LOC WHERE RESC_NAME = *resc){
        *svr=*r.RESC_LOC;
    }
    writeLine("serverLog", "\nConnecting on *resc - *svr");

    msiGetObjType(*archColl, *inputType);
    if (*inputType like '-d'){
         writeLine("stdout","Checking data status: *archColl");
        *count = checkTapeFile(*resc, *svr, *archColl, *dmfs_attr, *dataPathList);
    }
    if (*inputType like '-c'){
        writeLine("stdout","Checking collection status: *archColl");
        *count = checkTapeCollection(*resc, *svr, *archColl, *dmfs_attr, *dataPathList);
    }

    uuChopPath(*archColl, *dir, *projectCollection);
    uuChopPath(*dir, *dir2, *project);

    # Open collection to update status AVU *archiveState
    openProjectCollection(*project, *projectCollection, *aclChange, 'own');

    *value = "Number of files to bring back online: *count";
    setCollectionAVU(*archColl, *stateAttrName, *value)

    *unMigratingCounter = 0;
    *offlineList = "";
    *unMigratingList  = "";
    *unArchivingList  = "";

    # Check if data list is not empty -> if true some data can be un-archived
    if (*dataPathList !=  ""){
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
        prepare_unarch();
    }

    # UnMigrating Check
    if (*unMigratingList != ""){
        writeLine("serverLog", "Unmagrating to cache: *unMigratingList");
        *value = "*unMigratingCounter";
        setCollectionAVU(*archColl, *stateAttrName, *value)

        # Delay & recursive call
        delay("<PLUSET>30s</PLUSET>"){
            writeLine("serverLog", "SURFSara Archive - delay 30s, before retry");
            prepare_unarch();
        }
    }
    else{
        # UnArchive Check
        if (*unArchivingList != ""){
            *value = "start-transfer";
            setCollectionAVU(*archColl, *stateAttrName, *value)
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