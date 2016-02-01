# Call with
#
# Needs iRODS admin right
#
# irule -F create-ingest.r "*token='bla-token'" "*user='p.vanschayck'" "*project='foo'" "*machine='bar'" "*existingDir=''"

createIngest {
    *tokenColl = /ritZone/ingest/*token;

    *code = errorcode(msiCollCreate(*tokenColl, 0, *status));

    if ( *code == -809000 ) {
        failmsg(-1, "Token already in use");
    } else if ( *code != 0 ) {
        fail(*code);
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "machine", *machine);
    msiAssociateKeyValuePairsToObj(*metaKV, "*tokenColl", "-C");

    if ( *existingDir != "" ) {
        *phyDir = *existingDir
    } else {
        *phyDir = "/mnt/ingest/" ++ *token
        msiExecCmd("enable-ingest-zone.sh", *user ++ " " ++ *phyDir, "null", "null", "null", *status);
    }

    msiPhyPathReg(*tokenColl, "nfsResc", *phyDir, "mountPoint", *status);

    msiSetACL("default", "own", *user, *tokenColl)
}

INPUT *user="",*token="",*machine="",*project="",*existingDir=""
OUTPUT ruleExecOut
