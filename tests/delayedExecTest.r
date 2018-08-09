# Call with
#
# irule -F delayedExecTest.r "*pluset='1h'"

irule_dummy() {
    IRULE_delayedExecTest(*pluset);
}

IRULE_delayedExecTest(*pluset) {
    # Convert epoch timestamp to date & time
    *ts = timestrf(time(), "%s");
    *fmt = "%.4d-%.2d-%.2d:%.2d:%.2d:%.2d";
    msi_time_ts2str( int(*ts) + 7200, *fmt, *strtime ); # Add 7200 seconds for UTC+2

    # Write stdout debug message
    writeLine("stdout", "Current time is *strtime UTC. Adding to queue with delay of *pluset");

    delay("<PLUSET>*pluset</PLUSET>") {
        # Write delayed rodsLog message
        msiWriteRodsLog("This message should appear *pluset after *strtime UTC", 0);
    }
}

INPUT *pluset=""
OUTPUT ruleExecOut