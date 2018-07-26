# Move projectCollection to SURFsara tape
#
# Call with
# irule -F archiveUMProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'" "*archResc='ires-centosResource'"

irule_dummy() {
    IRULE_archiveUMProjectCollection(*project, *projectCollection, *archResc);
}

IRULE_archiveUMProjectCollection(*project, *projectCollection, *archResc) {
    # Open project collection
    openProjectCollection(*project, *projectCollection, 'service-surfarchive', 'own')

    # Obtain the project resource from the project
    getCollectionAVU("/nlmumc/projects/*project","resource",*sourceResource,"","true");

    # TODO: This does not lead to the resource host, as only the children of a repl resource have the resource host specified
    #foreach (*r in select RESC_LOC where RESC_NAME = *sourceResource) {
    #    *sourceResourceHost = *r.RESC_LOC;
    #}
    # Hardcoded workaround:
    foreach (*r in select RESC_LOC where RESC_NAME = 'UM-hnas-4k') {
        *sourceResourceHost = *r.RESC_LOC;
    }

    # Start tar'ing on resource host which will contain the files
    remote(*sourceResourceHost, "") {
        tarProjectCollection("/nlmumc/projects/*project/*projectCollection", *sourceResource, *sourceResource, *archResc)
    }

    *tar = "/nlmumc/projects/*project/*projectCollection/"++*projectCollection++".tar"

    # Perform checksum checks on both source resource and destination resource. As this is a long distance transfer
    msiDataObjChksum(*tar, "verifyChksum=++++ChksumAll=", *chkSum);

    # Trim away the remaining copy on source resource
    msiDataObjTrim(*tar, *sourceResource, "1", "1", "null", *Status);

    # Close project collection
    closeProjectCollection(*project, *projectCollection);

    foreach ( *Row in select DATA_ACCESS_USER_ID where COLL_NAME = "/nlmumc/projects/*project/*projectCollection" and DATA_NAME = "*projectCollection.tar" ) {
        *objectID = *Row.DATA_ACCESS_USER_ID;

        *O = select USER_NAME, USER_TYPE where USER_ID = '*objectID';
        foreach (*R in *O) {
            *objectName = *R.USER_NAME;
            *objectType = *R.USER_TYPE;
        }

        # Ignore service-surfarchive
        if ( *objectName != 'service-surfarchive' ) {
            msiSetACL("default", "admin:null", *objectName, *tar);
        }
    }

    msiSetACL("default", "admin:write", 'service-surfarchive', *tar);
}

INPUT *project='', *projectCollection='', *archResc=''
OUTPUT ruleExecOut
