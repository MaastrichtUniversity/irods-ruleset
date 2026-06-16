pep_api_data_obj_copy_post(*INSTANCE_NAME, *COMM, *DATAOBJCOPYINP, *TRANSSTAT) {
    # Policy to increment the size of the ingested files for the progress bar for direct ingests
    if(*DATAOBJCOPYINP.dst_obj_path like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
        *resource = "";
        *creator = "";
        *sizeIngested = 0;
        *sizeToAdd = "0";
        uuChop(*DATAOBJCOPYINP.dst_obj_path, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);
        uuChop(*tail, *collection, *tail, "/", true);
        # Get the creator AVU from the collection, if it exists, that means the collection already is fully ingested
        getCollectionAVU("/nlmumc/projects/*project/*collection","creator",*creator,"","false");
        if(*creator == ""){
            foreach(*key in *DATAOBJCOPYINP){
                # This key is not always available, it is available when the pep is triggered from 'irsync' but not from 'icp'
                if(*key == "dst_dataSize"){
                    *sizeToAdd = *DATAOBJCOPYINP.dst_dataSize;
                }
            }
            getCollectionAVU("/nlmumc/projects/*project/*collection","sizeIngested",*sizeIngested,"","false");
            *sizeIngested = *sizeIngested + double(*sizeToAdd);
            msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
            msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C")
        }
    }
}