
dmget(*data, *svr){
    msiExecCmd("dmget", "*data", "*svr", "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*dmStat);
    msiWriteRodsLog("DEBUG: $userNameClient:$clientAddr- Archive dmget started on *svr:*data. Returned Status- *dmStat.", 0);
}
