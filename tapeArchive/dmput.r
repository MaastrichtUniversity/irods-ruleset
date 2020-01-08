# Force a collection offline

dmput(){
    *resc = "arcRescSURF01";
    foreach(
        *r in SELECT
                RESC_LOC
            WHERE
                RESC_NAME = *resc
    ){
        *svr=*r.RESC_LOC;
    }
    writeLine("stdout",*archColl );
    writeLine("stdout","*svr");          #Whitespace for display
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
#
    }

    writeLine("stdout", *dataPathList);

    msiExecCmd("dmput", *dataPathList, "*svr", "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*Out);

    *Out=trimr(*Out,'\n');
    writeLine("stdout", *Out);
}
INPUT *archColl=""
OUTPUT ruleExecOut
