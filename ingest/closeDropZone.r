# Call with
#
# irule -F closeDropZone.r "*token='bla-token'"

irule_dummy() {
    IRULE_closeDropZone(*token)
}

IRULE_closeDropZone(*token) {

    *srcColl = "/nlmumc/ingest/zones/*token"

    getCollectionAVU(*srcColl,"project",*project,"","true");
    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");

    # Obtain the resource host from the specified ingest resource
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
        *ingestResourceHost = *r.RESC_LOC;
    }

    msiWriteRodsLog("Closing dropzone *token from project *project on resource host *ingestResourceHost", 0);

    # TODO: Handle errors
    # The unmounting of the physical mount point is not done in the delay() where msiRmColl on the token is done.
    # This is because of a bug in the unmount. This is kept in memory for
    # the remaining of the irodsagent session.
    # See also: https://groups.google.com/d/msg/irod-chat/rasDT-AGAVQ/Bb31VJ9SAgAJ
    *code = errorcode(msiPhyPathReg(*srcColl, "", "", "unmount", *status));

    delay("<PLUSET>1s</PLUSET>") {

        msiRmColl(*srcColl, "forceFlag=", *OUT);

        # Disabling the ingest zone needs to be executed on remote ires server
        remote(*ingestResourceHost,"") {
            msiExecCmd("disable-ingest-zone.sh", "/mnt/ingest/zones/" ++ *token, "null", "null", "null", *OUT);
        }
    }
}

INPUT *token=''
OUTPUT ruleExecOut