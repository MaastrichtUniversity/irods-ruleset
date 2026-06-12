pep_api_data_obj_put_post(*INSTANCE_NAME, *COMM, *DATAOBJINP, *BUFFER, *PORTAL_OPR_OUT) {
    # Policy to increment the size of the ingested files for the progress bar for mounted ingests
    if(*DATAOBJINP.obj_path like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
        *resource = "";
        *creator = "";
        *sizeIngested = 0;
        *sizeToAdd = "0";
        uuChop(*DATAOBJINP.obj_path, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);
        uuChop(*tail, *collection, *tail, "/", true);
        # Get the creator AVU from the collection, if it exists, that means the collection already is fully ingested
        getCollectionAVU("/nlmumc/projects/*project/*collection","creator",*creator,"","false");
        if(*creator == ""){
            foreach(*key in *DATAOBJINP){
                if(*key == "dataSize"){
                    *sizeToAdd = *DATAOBJINP.dataSize;
                }
            }
            getCollectionAVU("/nlmumc/projects/*project/*collection","sizeIngested",*sizeIngested,"","false");
            *sizeIngested = *sizeIngested + double(*sizeToAdd);
            msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
            msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C")
        }
    }
}