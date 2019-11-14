
dmget(*data, *svr){
    msiExecCmd("dmget", "*data", "*svr", "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*dmStat);
    writeLine("serverLog","$userNameClient:$clientAddr- Archive dmget started on *svr:*data. Returned Status- *dmStat.");
}
