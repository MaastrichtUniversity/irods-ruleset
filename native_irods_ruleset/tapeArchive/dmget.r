
dmget(*data, *svr){
    msiExecCmd("dmget", "'*data'", "*svr", "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*dmStat);
    msiWriteRodsLog("DEBUG: $userNameClient:$clientAddr- Archive dmget started on *svr:*data. Returned Status- *dmStat.", 0);
    msiGetStderrInExecCmdOut(*dmRes,*Err);
    if ( strlen(*Err) > 0 ) {
        msiWriteRodsLog("Error occured during dmattr", 0)
        msiWriteRodsLog(*Err, 0)
    }
}
