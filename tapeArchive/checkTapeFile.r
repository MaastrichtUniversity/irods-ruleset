
checkTapeFile(*resc, *svr, *archColl, *dmfs_attr, *dataPathList){
    uuChopPath(*archColl, *dir, *dataName);
    *count = 1 ;
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
        *ipath = *row.COLL_NAME++"/"++*row.DATA_NAME;
        *dataPathList = *row.DATA_PATH;
        msiWriteRodsLog("DEBUG: dataPath *dataPathList", 0);
        dmattr(*dataPathList, *svr, *count, *dmfs_attr);
    }
    # Return *count
    "*count"
}