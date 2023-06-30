# Call with
#
# Needs iRODS admin right
#
# irule -F /rules/native_irods_ruleset/ingest/createRemoteDirectory.r "*project='P000000001'" "*token='bla-token'" "*voPersonExternalID='p.vanschayck@unimaas.nl'"

createRemoteDirectory(*project, *token, *voPersonExternalID) {
    *dropzonePath="/nlmumc/ingest/zones/*token"

    *ingestResource = "";
    getCollectionAVU("/nlmumc/projects/*project","ingestResource",*ingestResource,"","true");
    foreach (*r in select RESC_LOC where RESC_NAME = *ingestResource) {
        *ingestResourceHost = *r.RESC_LOC;
    }

    # Enabling the ingest zone needs to be done on the remote server
    remote(*ingestResourceHost, "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME>") {
        *phyDir = "/mnt/ingest/zones/" ++ *token;
        msiExecCmd("enable-ingest-zone.sh", *voPersonExternalID ++ " " ++ *phyDir, "null", "null", "null", *status);
    }
}
