# Move projectCollection to SURFsara tape
#
# Call with
# irule -F archiveUMProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'" "*archResc='ires-centosResource'"

irule_dummy() {
    IRULE_archiveUMProjectCollection(*project, *projectCollection, *archResc);
}

IRULE_archiveUMProjectCollection(*project, *projectCollection, *archResc) {
    # Open project collection
    openProjectCollection(*project, *projectCollection)

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
    msiDataObjTrim(*tar, *sourceResource, "1", "1", "null", *Status)

    # Close project collection
    closeProjectCollection(*project, *projectCollection)
}

INPUT *project='', *projectCollection='', *archResc=''
OUTPUT ruleExecOut
