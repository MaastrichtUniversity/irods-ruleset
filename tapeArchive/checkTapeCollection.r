

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
        *ipath=*row.COLL_NAME++"/"++*row.DATA_NAME;
        *dataPath = *row.DATA_PATH;
        writeLine("serverLog", "\tdataPath *dataPath");
        if ( *dataPathList == ""){
            *dataPathList = *dataPath;
        }
        else{
            *dataPathList = *dataPathList++" "++*dataPath;
        }
        *count = *count + 1;
    }
    if (*dataPathList !=  ""){
        dmattr(*dataPathList, *svr, *ipath, *count, *dmfs_attr);
    }
    else{
        *dmfs_attr."result" = "null";
    }
    # Return *count
    "*count"
}