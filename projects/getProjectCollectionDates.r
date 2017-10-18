# Call with
#
# irule -F getProjectCollectionDates.r "*project='P000000001'" "*projectCollection='C000000002'"

irule_dummy() {
    IRULE_getProjectCollectionDates(*project, *projectCollection, *result);
    writeLine("stdout", *result);
}

IRULE_getProjectCollectionDates(*project, *projectCollection,*result) {
    *json_str = '[]';
    msiString2KeyValPair("", *kvp);
    *o = "";
    *fmt = "%.4d-%.2d-%.2dT%.2d:%.2d:%.2dZ";
    
    foreach ( *Row in select DATA_CREATE_TIME,DATA_MODIFY_TIME,COLL_CREATE_TIME,COLL_MODIFY_TIME where COLL_NAME == "/nlmumc/projects/*project/*projectCollection" AND DATA_NAME == 'metadata.xml' ) {
        msi_time_ts2str( int(*Row.DATA_CREATE_TIME), *fmt, *DATA_CREATE_TIME );
        msi_time_ts2str( int(*Row.DATA_MODIFY_TIME), *fmt, *DATA_MODIFY_TIME ); 
        msi_time_ts2str( int(*Row.COLL_CREATE_TIME), *fmt, *COLL_CREATE_TIME );
        msi_time_ts2str( int(*Row.COLL_MODIFY_TIME), *fmt, *COLL_MODIFY_TIME );
        
        msiAddKeyVal(*kvp, 'metadataCreate', *DATA_CREATE_TIME);
        msiAddKeyVal(*kvp, 'metadataModify', *DATA_MODIFY_TIME);
        msiAddKeyVal(*kvp, 'collectionCreate', *COLL_CREATE_TIME);
        msiAddKeyVal(*kvp, 'collectionModify', *COLL_MODIFY_TIME);
        
       
    }

    msi_json_objops(*o, *kvp, "set");
    
    *result = *o;
}

INPUT *project="P000000001", *projectCollection='C000000001'
OUTPUT ruleExecOut