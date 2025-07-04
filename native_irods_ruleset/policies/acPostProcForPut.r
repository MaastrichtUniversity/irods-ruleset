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
            ##   This policy will fire twice for every file (replicated resources) or once for passthru resources (um-hnas)
            ##   For mounted ingest, it will create replNum 0 and 1 (replicated) or 0 (passthru), because these are the first copies of the data
            ##   Both will fire with replNum = 0, so that is why we choose that one here
            # The above is irrelevant for now due to a bug found whilst working on DHDO-1731. For more info, see test_pep_api_data_obj_put_post
              if(str($replNum) == "1") {
                   getCollectionAVU("/nlmumc/projects/*project/*collection","sizeIngested",*sizeIngested,"","false");
                   *sizeIngested = *sizeIngested + double($dataSize);
                   msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
                   msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C")
              }
        }
    }

    # Policy to give read access on metadata files to dropzone creator
    if ($objPath like regex "/nlmumc/ingest/direct/.*/instance.json" || $objPath like regex "/nlmumc/ingest/direct/.*/schema.json"){
        msiSetACL("default", "read", "$userNameClient", "$objPath")
    }
}
