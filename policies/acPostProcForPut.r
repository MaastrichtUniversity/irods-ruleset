acPostProcForPut {
    # Policy to increment the size of the ingested files for the progress bar
    if($objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
        *resource = "";
        *sizeIngested = 0;
        uuChop($objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);
        uuChop(*tail, *collection, *tail, "/", true);
        getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
        if( *resource == $rescName ) {
            foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project/*collection") {
                if ( *av.META_COLL_ATTR_NAME == "sizeIngested" ) {
                    *sizeIngested = double(*av.META_COLL_ATTR_VALUE);
                }
            }
            *sizeIngested = *sizeIngested + double($dataSize);
            msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
            msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
        }
    }

    # Policy to give read access on metadata files to dropzone creator
    if ($objPath like regex "/nlmumc/ingest/direct/.*/instance.json" || $objPath like regex "/nlmumc/ingest/direct/.*/schema.json"){
        msiSetACL("default", "read", "$userNameClient", "$objPath")
    }
}