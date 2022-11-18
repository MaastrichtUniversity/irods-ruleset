# https://docs.irods.org/4.2.11/getting_started/upgrading/#migrating-from-static-peps-to-dynamic-peps
# https://docs.irods.org/4.2.11/plugins/dynamic_policy_enforcement_points/


# Print all key value in one of the parameters:
#  msiWriteRodsLog("INFO: pep_api_data_obj_put_post", *status);
#      writeLine("serverLog", *DATAOBJINP);
#         foreach (*I in *DATAOBJINP) {
#             writeLine("serverLog", *I++"="++*DATAOBJINP.*I)
#         }

pep_api_data_obj_put_post(*INSTANCE_NAME, *COMM, *DATAOBJINP, *BUFFER, *PORTAL_OPR_OUT){
    *objPath = *DATAOBJINP.obj_path
    # Policy to increment the size of the ingested files for the progress bar
    if(*objPath like regex "/nlmumc/projects/P[0-9]{9}/C[0-9]{9}/.*") {
        *resource = "";
        *sizeIngested = 0;
        *rescName = ""
        if (exists(*DATAOBJINP,"destRescName")){
            *rescName = *DATAOBJINP.destRescName
        }
        uuChop(*objPath, *head, *tail, "/nlmumc/projects/", true);
        uuChop(*tail, *project, *tail, "/", true);
        uuChop(*tail, *collection, *tail, "/", true);
        getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
        if( *resource == *rescName ) {
            foreach (*av in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME == "/nlmumc/projects/*project/*collection") {
                if ( *av.META_COLL_ATTR_NAME == "sizeIngested" ) {
                    *sizeIngested = double(*av.META_COLL_ATTR_VALUE);
                }
            }
            *sizeIngested = *sizeIngested + double(*DATAOBJINP.data_size);
            msiAddKeyVal(*metaKV,  'sizeIngested', str(*sizeIngested));
            msiSetKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");
        }
    }

    # Policy to give read access on metadata files to dropzone creator
    if (*objPath like regex "/nlmumc/ingest/direct/.*/instance.json" || *objPath like regex "/nlmumc/ingest/direct/.*/schema.json"){
        msiSetACL("default", "read", "$userNameClient", "*objPath")
    }
}

exists(*list, *key) {
    errormsg(msiGetValByKey(*list, *key, *val), *err) == 0;
}
