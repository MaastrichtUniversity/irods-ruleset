
dmattr(*data, *svr, *count, *dmfs_attr){
    msiExecCmd("dmattr", *data, *svr, "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*Out);

    # Our *Out variable looks something like this "109834fjksjv09sdrf+DUL+0+2014"
    # The + is a separator, and the order of the 4 values are BFID, DMF status, size of data on disk, total size of data.
    # If *Out contains multiple files, one line = one file
    *pathList = *data;
    msiWriteRodsLog("DEBUG: Result:", 0);
    for ( *i=0; *i < *count ; *i = *i +1){
        uuChop(*Out, *firstResult, *nextResult, "\n", true);
        *Out = *nextResult;
        uuChop(*pathList, *firstPath, *nextPath, '" ', true);
        *pathList = *nextPath;

        *result = *firstResult;
        #DMF STATUS, trims up the DMF status only
        *dmfs=triml(trimr(trimr(*result,'+'),'+'),'+');

        if ( *i != *count -1){
            *file = *firstPath;
            msiWriteRodsLog("DEBUG: \t*dmfs *file", 0);
            *dmfs_attr.*file = *dmfs;
        }
        else{
            *file = *nextPath;
            msiWriteRodsLog("DEBUG: \t*dmfs *file", 0);
            *dmfs_attr.*file = *dmfs;
        }
    }
}