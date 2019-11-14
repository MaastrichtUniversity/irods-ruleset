# Call with
#
# NOT RECOMMENDED to be called with irule, since it is part of a greater workflow and has to be called from within prepareTapeArchive.r rule

tapeArchive(*archColl, *counter, *rescParentsLocation, *dataPerResources, *rescParentsName){
    *stateAttrName = "archiveState";
    *archiveResc="arcRescSURF01";
    # Count how many file have been archived
    *isMoved=0;

    foreach(*srcResourceId in *rescParentsLocation) {
        # Get the coordinating resource name
        *coordResourceName = *rescParentsName.*srcResourceId;

        # Get the data array in *dataPerResources by the *coordResourceName
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, '*coordResourceName', '');
        msi_json_objops(*dataPerResources, *kvp, "get");
        *dataArray = *kvp.*coordResourceName;

        # Get the data array size
        *size = 0;
        msi_json_arrayops(*dataArray , "", "size", *size);

        # Get the resource host location
        *resourceHostLocation= *rescParentsLocation.*srcResourceId;

        if ( *size > 0 ){
            # Do a remote execution on *resourceHostLocation
            remote(*resourceHostLocation,"") {
                for (*index=0; *index < *size; *index = *index + 1) {
                    # Get the data's path by its index in *dataArray
                    *dataPath = "";
                    msi_json_arrayops(*dataArray, *dataPath, "get", *index)
                    writeLine("serverLog","*dataPath");

                    # Update state AVU with progress
                    # Collection have been opened in prepareTapeArchive
                    # Otherwise update will failed
                    *value = "archive-in-progress "++str(*isMoved+1)++"/"++str(*counter);
                    setCollectionAVU(*archColl,*stateAttrName,*value);

                    # Calculate data checksum
                    msiDataObjChksum(*dataPath,"verifyChksum=",*chksum);

                    # Replicate data from *coordResourceName to *archiveResc
                    msiDataObjRepl(*dataPath, "destRescName=*archiveResc++++verifyChksum=", *moveStatus);
                    if ( *moveStatus != 0 ) {
                       failmsg(-1, "Replication of *ipath from *coordResourceName to *archiveResc FAILED.");
                    }

                    # Trim data from *coordResourceName
                    msiDataObjTrim(*dataPath, *coordResourceName, "null", "1", "null", *trimStatus);
                    if ( *trimStatus != 1 ) {
                       failmsg(-1, "Trim *ipath from *coordResourceName FAILED.");
                    }

                    # Update counter
                    *isMoved=*isMoved+1;

                    # Report logs
                    writeLine("serverLog","\t\tchksum done "++str(*chksum));
                    writeLine("serverLog","\t\trepl moveStat done "++str(*moveStatus));
                    writeLine("serverLog","\t\ttrim stat done "++str(*trimStatus));
                    writeLine("serverLog","\t\tReplicate from "++*coordResourceName++" to "++*archiveResc);
                }
            }
        }
    }
    # Update state AVU to done
    setCollectionAVU(*archColl, *stateAttrName, "archive-done")
    writeLine("serverLog","surfArchiveScanner archived "++str(*isMoved)++" files.");

    # Delete state AVU
    msiAddKeyVal(*delKV, *stateAttrName, "archive-done");
    msiRemoveKeyValuePairsFromObj(*delKV,*archColl, "-C");

    # Get project's id and collection's id
    uuChopPath(*archColl, *dir, *projectCollection);
    uuChopPath(*dir, *dir2, *project);

    # Re-calculate new values for dcat:byteSize and numFiles
    setCollectionSize(*project, *projectCollection, 'false', 'false');
    writeLine("stdout","dcat:byteSize and numFiles have been re-calculated and adjusted");

    # Close collection by making all access read only
    closeProjectCollection(*project, *projectCollection);
}