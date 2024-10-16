
dmattr(*data, *svr, *Out){
    # This part is always called remotely on the tape server
    msiExecCmd("dmattr", *data, *svr, "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*Out);
}