# Call with
#
# irule -F /rules/misc/getCollectionStatistics.r "*project='P000000001'" "*projectCollection='C000000002'"

irule_dummy() {
    IRULE_getCollectionStatistics(*project, *projectCollection,*result);
    writeLine("stdout", *result);
}

IRULE_getCollectionStatistics(*project, *projectCollection,*result) {
    *projectTitle = '';
    *collectionTitle = '';
    *dates = '';
    msiString2KeyValPair("", *kvp);
    *fmt = "%.4d-%.2d-%.2dT%.2d:%.2d:%.2dZ";

    #Titel of the collection
    getCollectionAVU("/nlmumc/projects/*project/*projectCollection",'title', *collectionTitle ,'' ,'true');
    msiAddKeyVal(*kvp, 'collectionTitle', *collectionTitle);

     #Titel of the collection
    getCollectionAVU("/nlmumc/projects/*project",'title', *projectTitle ,'' ,'true');
    msiAddKeyVal(*kvp, 'projectTitle', *projectTitle);

    #Size of collection
    getProjectCollectionSize(*project, *projectCollection,*size);
    msiAddKeyVal(*kvp, 'collectionSize', *size);

    #Create and modify date of metadata.xml  and  Create and modify date of  the collection
    getProjectCollectionDates(*project, *projectCollection,*dates);
    *json_str = *dates

    #Get current time
    msiGetIcatTime(*time,"unix")
    msi_time_ts2str( int(*time), *fmt, *timeutc );
    msiAddKeyVal(*kvp, 'timestamp', *timeutc);

    #Create irods path
    msiAddKeyVal(*kvp, 'irodsPath', "/nlmumc/projects/*project/*projectCollection");

    #create Project ID
    msiAddKeyVal(*kvp, 'projectID', "*project");

    #create Project ID
    msiAddKeyVal(*kvp, 'collectionID', "*projectCollection");

    #Create JSON for output
    msi_json_objops(*json_str, *kvp, "add");
    *result = *json_str;

}

INPUT *project="P000000001", *projectCollection='C000000001'
OUTPUT ruleExecOut