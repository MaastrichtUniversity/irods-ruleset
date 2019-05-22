# Call with
#
# Needs iRODS admin right
#
# irule -F create-ingest.r "*token='bla-token'" "*user='p.vanschayck'" "*project='P000000001'" "*title='bar'"

createIngest {
    *hasDropZonepermission = "";
    checkDropZoneACL(*user, *hasDropZonepermission);
    if (*hasDropZonepermission == "false") {
        failmsg(-1, "User '*user' has insufficient DropZone permissions on /nlmumc/ingest/zones");
    }

    *tokenColl = "/nlmumc/ingest/zones/*token";

    *code = errorcode(msiCollCreate(*tokenColl, 0, *status));

    if ( *code == -809000 ) {
        failmsg(-1, "Token already in use");
    } else if ( *code != 0 ) {
        fail(*code);
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);
    #msiAddKeyVal(*metaKV, "author", *user);
    msiAddKeyVal(*metaKV, "state", "open");
    msiAssociateKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

    # Obtain the resource host from the specified ingest resource
    *ingestResource = "";
    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
        *ingestResourceHost = *r.RESC_LOC;
    }


    # Enabling the ingest zone needs to be done on the remote server
    remote(*ingestResourceHost,"") {
        *phyDir = "/mnt/ingest/zones/" ++ *token;
        msiExecCmd("enable-ingest-zone.sh", *user ++ " " ++ *phyDir, "null", "null", "null", *status);

        # Get the value for ingestResource again, in order to prevent SYS_HEADER_READ_LEN errors with msiPyPathReg
        getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
        msiPhyPathReg(*tokenColl, *ingestResource, *phyDir, "mountPoint", *status);
    }

    # Set the ACL's on the iRODS collection (for both the current user and service-account)
    msiSetACL("default", "own", *user, *tokenColl);
    msiSetACL("default", "own", "service-dropzones", *tokenColl);

}

INPUT *user="",*token="",*project="",*title=""
OUTPUT ruleExecOut
