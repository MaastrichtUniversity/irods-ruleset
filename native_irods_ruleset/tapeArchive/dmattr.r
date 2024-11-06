
dmattr(*data, *svr, *Out){
    # This part is always called remotely on the tape server
    # This is quoted because dmattr does not support spaces
    msiExecCmd("dmattr", "'*data'", *svr, "", "", *dmRes);
    msiGetStdoutInExecCmdOut(*dmRes,*Out);
    msiGetStderrInExecCmdOut(*dmRes,*Err);
    if ( strlen(*Err) > 0 ) {
        msiWriteRodsLog("Error occured during dmattr", 0)
        msiWriteRodsLog(*Err, 0)
    }
}