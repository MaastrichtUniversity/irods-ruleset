# Gets fired after a file is PUT into iRODS
acPostProcForPut {
    # Policy to increment the size of the ingested files for the progress bar
    if($objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
         *resource = "";
         *creator = "";
         *sizeIngested = 0;
         uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
         uuChop(*tail, *project, *tail, "/", true);
         uuChop(*tail, *collection, *tail, "/", true);
         # Get the creator AVU from the collection, if it exists, that means the collection already is fully ingested
         getCollectionAVU("/nlmumc/projects/*project/*collection","creator",*creator,"","false");
         if(*creator == ""){
             # If the connection option is irsync, this means we are in a mounted ingest
             if($connectOption == "irsync") {
                 getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
                 if( *resource == $rescName ) {
                     getCollectionAVU("/nlmumc/projects/*project/*collection","sizeIngested",*sizeIngested,"","false");
                     *sizeIngested = *sizeIngested + double($dataSize);
                     msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
                     msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
                 }
             }
             else {
                 # We are in a direct ingest, that means that there are 3 copies of the data in total (0-stagingresc, 1 and 2)
                 # We only need to count one of these three replicas towards the sizeIngested total
                 if(str($replNum) == "2") {
                     *creator = "";
                     getCollectionAVU("/nlmumc/projects/*project/*collection","sizeIngested",*sizeIngested,"","false");
                     *sizeIngested = *sizeIngested + double($dataSize);
                     msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
                     msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
                 }
             }
        }
    }

    # Policy to give read access on metadata files to dropzone creator
    if ($objPath like regex "/nlmumc/ingest/direct/.*/instance.json" || $objPath like regex "/nlmumc/ingest/direct/.*/schema.json"){
        msiSetACL("default", "read", "$userNameClient", "$objPath")
    }
}
