# Move SURFsara tape archive back to UM
#
# Call with
# irule -F unArchiveUMProjectCollection.r "*project='P000000001'" "*projectCollection='C000000001'"

irule_dummy() {
    IRULE_unArchiveUMProjectCollection(*project, *projectCollection);
}

IRULE_unArchiveUMProjectCollection(*project, *projectCollection) {
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

    # Start untar'ing on resource host which will contain the file
    remote(*sourceResourceHost, "") {
        untarProjectCollection("/nlmumc/projects/*project/*projectCollection/"++*projectCollection++".tar", *sourceResource)
    }

    # Close project collection
    closeProjectCollection(*project, *projectCollection)
}

INPUT *project='', *projectCollection=''
OUTPUT ruleExecOut