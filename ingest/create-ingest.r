# Call with
#
# Needs iRODS admin right
#
# irule -F create-ingest.r "*token='bla-token'" "*user='p.vanschayck'" "*project='P000000001'" "*title='bar'" "*existingDir=''"

createIngest {
    
    *tokenColl = "/nlmumc/ingest/zones/*token";

    *code = errorcode(msiCollCreate(*tokenColl, 0, *status));

    if ( *code == -809000 ) {
        failmsg(-1, "Token already in use");
    } else if ( *code != 0 ) {
        fail(*code);
    }

    msiAddKeyVal(*metaKV, "project", *project);
    msiAddKeyVal(*metaKV, "title", *title);
    msiAddKeyVal(*metaKV, "state", "open");
    msiAssociateKeyValuePairsToObj(*metaKV, *tokenColl, "-C");

    # Obtain the resource host from the specified ingest resource
    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
        *ingestResourceHost = *r.RESC_LOC;
    }


    # Enabling the ingest zone needs to be done on the remote server
    remote(*ingestResourceHost,"") {
        if ( *existingDir != "" ) {
            *phyDir = *existingDir;
        } else {
            *phyDir = "/mnt/ingest/zones/" ++ *token;
            msiExecCmd("enable-ingest-zone.sh", *user ++ " " ++ *phyDir, "null", "null", "null", *status);
        }

        msiPhyPathReg(*tokenColl, *ingestResource, *phyDir, "mountPoint", *status);
    }

    # Set the ACL's on the iRODS collection
    msiSetACL("default", "own", *user, *tokenColl);

}

INPUT *user="",*token="",*existingDir="",*project="",*title=""
OUTPUT ruleExecOut
