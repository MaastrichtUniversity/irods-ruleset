# Call with
# irule -F prepareTapeArchive.r "*archColl='/nlmumc/projects/P000000001/C000000097'"


prepareTapeArchive {
    # resource name destination
    *archiveResc="arcRescSURF01";
    # The minimum file size criteria (in bytes)
    *minimumSize=262144000;
    # rodsadmin user running the rule
    *aclChange="service-surfarchive";
    # state AVU attribute name -> to report progress
    *stateAttrName = "archiveState";

    # Query *stateAttrName value
    *stateValue = "";
    foreach (*av in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME == "*archColl" AND META_COLL_ATTR_NAME == *stateAttrName) {
        *stateValue = *av.META_COLL_ATTR_VALUE;
    }
    # Check for valid state to start archiving
    if ( *stateValue != "no-state-set" && *stateValue != "archive-done"  && *stateValue != "" ) {
        failmsg(-1, "Invalid state to start archiving.");
    }

    # Get project's id and collection's id
    uuChopPath(*archColl, *dir, *projectCollection);
    uuChopPath(*dir, *dir2, *project);
    # Open collection to modify state AVU &
    openProjectCollection(*project, *projectCollection, *aclChange, 'own');

    *dataPerResources = "";
    # Query all children resources info
    # Create *dataPerResources - json object: coordResourceName -> array [dataPath, ...]
    # -> create an empty array for each resources
    # Create *rescParentsLocation - key pair value variable:  resourceParentId -> resourceHostLocation
    # -> to execute a remote call on resource host
    # Create *rescParentsName - key pair value variable:  resourceParentId -> resourceParentName
    # -> msiDataObjTrim need a resource name as input (not the id ...)
    foreach (*r in select RESC_PARENT, RESC_LOC where RESC_LOC != 'EMPTY_RESC_HOST'){
        *resourceHostLocation = *r.RESC_LOC;
        *resourceParentId = *r.RESC_PARENT;

        if (*resourceParentId != ""){
            # Query the resource parent name by its ID
            foreach (*p in select RESC_NAME where RESC_ID = *resourceParentId ){
                *coordResourceName = *p.RESC_NAME
                *rescParentsName.*resourceParentId = *coordResourceName;
            }
            # Check if the parent resource was already added
            # Parent resource are duplicated in the query's result because of replicated resources
            # Duplicate doesn't keep *dataArray empty
            msiAddKeyVal(*kvp, '*coordResourceName', '');
            msi_json_objops(*dataPerResources, *kvp, "get");
            *dataArray = *kvp.*coordResourceName;
            if (str(*dataArray) == "<null>"){
                # Then add the parent resource in *dataPerResources & *rescParentsLocation
                msiString2KeyValPair("", *kvp);
                msiAddKeyVal(*kvp, '*coordResourceName', '[]');
                msi_json_objops(*dataPerResources, *kvp, "add");

                *rescParentsLocation.*resourceParentId = *resourceHostLocation;
            }
        }
    }
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
        # Build data full path
        *dataPath = *ScanColl.COLL_NAME++"/"++*ScanColl.DATA_NAME;

        # Get the coordinating resource name
        *resourceParentId = *ScanColl.RESC_PARENT;
        *coordResourceName = *rescParentsName.*resourceParentId;

        # Add new data path entry to *dataArray in *dataPerResources
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, '*coordResourceName', '*dataPath');
        msi_json_objops(*dataPerResources, *kvp, "add");

        *counter=*counter+1;
	}
    writeLine("serverLog","surfArchiveScanner found "++str(*counter)++" files.");
    *value = "Number of files to be put offline: *counter";
    setCollectionAVU(*archColl, "archiveState", *value)

    # Delay before replication
    delay("<PLUSET>1s</PLUSET>") {
        tapeArchive(*archColl, *counter, *rescParentsLocation, *dataPerResources, *rescParentsName);
    }
}

INPUT *archColl=""
OUTPUT ruleExecOut