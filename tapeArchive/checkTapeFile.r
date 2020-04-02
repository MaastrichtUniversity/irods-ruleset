
checkTapeFile(*resc, *svr, *archColl, *dmfs_attr, *dataPathList){
    *dataPathList = "";
    uuChopPath(*archColl, *dir, *dataName);
    *count = 0;
    foreach(
        *row in
            SELECT
                    DATA_PATH,
                    COLL_NAME,
                    DATA_NAME
            WHERE
                    DATA_RESC_NAME = '*resc'
                AND COLL_NAME  = '*dir'
                AND DATA_NAME  = '*dataName'
    ){
        *dataPathList = *row.DATA_PATH;
        *count = *count + 1;
    }

    if (*dataPathList !=  ""){
        msiWriteRodsLog("DEBUG: dataPath *dataPathList", 0);
        dmattr(*dataPathList, *svr, *count, *dmfs_attr);
    }
    else{
       *dmfs_attr."result" = "null";
    }

    # Return *count
    "*count"
}