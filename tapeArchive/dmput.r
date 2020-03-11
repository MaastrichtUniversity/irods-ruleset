# Force a collection offline

dmput(){
    # TODO Change to parameter
    *resc = "arcRescSURF01";
    foreach(
        *r in SELECT
                RESC_LOC
            WHERE
                RESC_NAME = *resc
    ){
        *svr=*r.RESC_LOC;
    }
    msiWriteRodsLog("DEBUG: *archColl", 0);
    msiWriteRodsLog("DEBUG: *svr", 0);  #Whitespace for display
    *dataPathList = "";
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

    	if ( *dataPathList == ""){
            *dataPathList = *dataPath;
        }
        else{
            *dataPathList = *dataPathList++" "++*dataPath;
        }
    }

    msiWriteRodsLog("DEBUG: *dataPathList", 0);

    msiExecCmd("dmput", *dataPathList, "*svr", "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*Out);

    *Out=trimr(*Out,'\n');
    msiWriteRodsLog("DEBUG: *Out", 0);
}
INPUT *archColl=""
OUTPUT ruleExecOut
