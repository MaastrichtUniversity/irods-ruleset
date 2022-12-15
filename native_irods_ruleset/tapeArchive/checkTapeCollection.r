

checkTapeCollection(*resc, *svr, *archColl, *dmfs_attr, *dataPathList){
    *dataPathList = "";
    *count = 0;
    foreach(
        *row in
            SELECT
                  DATA_PATH,
                  COLL_NAME,
                  DATA_NAME
            where
                DATA_RESC_NAME = '*resc'
            AND COLL_NAME like '*archColl%'
    ){
        *dataPath = *row.DATA_PATH;
        msiWriteRodsLog("DEBUG: dataPath *dataPath", 0);
        if ( *dataPathList == ""){
            *dataPathList = '"*dataPath"';
        }
        else{
            *dataPathList = *dataPathList++" "++'"*dataPath"';
        }
        *count = *count + 1;
    }
    if (*dataPathList !=  ""){
        dmattr(*dataPathList, *svr, *count, *dmfs_attr);
    }
    else{
        *dmfs_attr."result" = "null";
    }
    # Return *count
    "*count"
}