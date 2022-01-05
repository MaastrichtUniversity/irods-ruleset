# Call with
#
# Needs iRODS admin right
#
# irule -F create-ingest.r "*token='bla-token'" "*user='p.vanschayck'" "*project='P000000001'" "*title='bar'" "*schema_name='DataHub_general_schema'" "*schema_version='0.0.1'"

createIngest {
    # Retrieve the domain username
    *voPersonExternalID = "";
    foreach( *U in select META_USER_ATTR_VALUE where USER_NAME = "*user" and META_USER_ATTR_NAME == "voPersonExternalID" ) {
        *voPersonExternalID = *U.META_USER_ATTR_VALUE;
    }
    if (*voPersonExternalID == "") {
        failmsg(-1, "User '*user' has no 'voPersonExternalID' value");
    }

    *hasDropZonepermission = "";
    checkDropZoneACL(*user, *hasDropZonepermission);
    if (*hasDropZonepermission == "false") {
        # -818000 CAT_NO_ACCESS_PERMISSION
        failmsg(-818000, "User '*user' has insufficient DropZone permissions on /nlmumc/ingest/zones");
    }

    # Check if the ingest resource is not down
    *ingestResource = "";
    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
        *ingestResourceHost = *r.RESC_LOC;
    }
    *ingestResourceStatus = ""
    foreach (*r in select RESC_STATUS where RESC_NAME = *ingestResource) {
        *ingestResourceStatus = *r.RESC_STATUS;
    }
    if (*ingestResourceStatus == "down") {
        failmsg(-1, "Ingest resource '*ingestResource' is down! Aborting");
    }

    # Create the dropzone
    *tokenColl = "/nlmumc/ingest/zones/*token";
    *code = errorcode(msiCollCreate(*tokenColl, 0, *status));

    if ( *code == -809000 ) {
        failmsg(-1, "Token already in use");
    } else if ( *code != 0 ) {
        fail(*code);
    }

    # Set dropzone AVUs
    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "schemaName", *schema_name);
    msiAddKeyVal(*metaKV, "schemaVersion", *schema_version);
    #msiAddKeyVal(*metaKV, "author", *user);
    msiAddKeyVal(*metaKV, "state", "open");
    msiAssociateKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

    # Enabling the ingest zone needs to be done on the remote server
    remote(*ingestResourceHost,"") {
        *phyDir = "/mnt/ingest/zones/" ++ *token;
        msiExecCmd("enable-ingest-zone.sh", *voPersonExternalID ++ " " ++ *phyDir, "null", "null", "null", *status);

        # Get the value for ingestResource again, in order to prevent SYS_HEADER_READ_LEN errors with msiPyPathReg
        getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
        msiPhyPathReg(*tokenColl, *ingestResource, *phyDir, "mountPoint", *status);
    }

    # Set the ACL's on the iRODS collection (for both the current user and service-account)
    msiSetACL("default", "own", *user, *tokenColl);
    msiSetACL("default", "own", "service-dropzones", *tokenColl);

}

INPUT *user="",*token="",*project="",*title=""*schema_name="",*schema_version=""
OUTPUT ruleExecOut
