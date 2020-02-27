#IRULE_estimateArchiveProjectCollection
irule_dummy() {
    IRULE_estimateProjectCollection(*project, *collection, *resultSize, *resultNumFiles);
    writeLine("stdout", *resultSize);
    writeLine("stdout", *resultNumFiles);
}

IRULE_estimateProjectCollection(*project, *collection, *resultSize, *resultNumFiles){

    *archColl = "/nlmumc/projects/*project/*collection"
    # Get the destination archive resource from the project
    getCollectionAVU("/nlmumc/projects/*project","ArchiveDestinationResource",*archiveResc,"N/A","true");
    *sizeBytes = 0;
    *minimumSize=262144000;        #The minimum file size (in bytes)
    *numFiles = 0;

    #Query 1- Find all flagged collections for Archive
    # CAUTION: using SUM(DATA_SIZE) inside SQL sums the size of all replicas, which is not what we want here
    foreach(*ScanColl in
       SELECT
              DATA_NAME,
              DATA_SIZE
       WHERE
              COLL_NAME = '*archColl' || like '*archColl/%'
              AND DATA_RESC_NAME != '*archiveResc'
              AND DATA_SIZE >= '*minimumSize'
    ){
        *sizeBytes = *sizeBytes + double(*ScanColl.DATA_SIZE);
        *numFiles = *numFiles + 1;
    }
    *resultSize =  str(*sizeBytes);
    *resultNumFiles =  str(*numFiles);
}

INPUT *project="", *collection=""
OUTPUT ruleExecOut