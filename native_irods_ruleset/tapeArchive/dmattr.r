
dmattr(*data, *svr, *count, *Out){
    msiExecCmd("dmattr", *data, *svr, "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*Out);
}